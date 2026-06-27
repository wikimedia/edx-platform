"""
Tests for the ``repair_asset_url_encoding`` management command helpers.

These cover the pure URL-normalization logic (no modulestore required).
"""

import ddt
from django.test import SimpleTestCase
from opaque_keys.edx.keys import CourseKey

from cms.djangoapps.contentstore.management.commands.repair_asset_url_encoding import (
    fully_unquote,
    normalize_asset_url,
    repair_text,
)

COURSE_KEY = CourseKey.from_string('course-v1:Org+Course+Run')


@ddt.ddt
class RepairAssetUrlEncodingHelpersTest(SimpleTestCase):
    """Unit tests for the normalization helpers."""

    @ddt.data(
        ('D%C3%ADa.jpg', 'Día.jpg'),
        ('D%25C3%25ADa.jpg', 'Día.jpg'),
        ('D%2525C3%2525ADa.jpg', 'Día.jpg'),
        ('D%252525C3%252525ADa.jpg', 'Día.jpg'),
        ('plain.png', 'plain.png'),
    )
    @ddt.unpack
    def test_fully_unquote(self, value, expected):
        assert fully_unquote(value) == expected

    @ddt.data(
        # Over-encoded /static/ links collapse to a single clean /static/ path.
        ('/static/D%252525C3%252525ADa.jpg', '/static/Día.jpg'),
        ('/static/D%25C3%25ADa.jpg', '/static/Día.jpg'),
        # A clean /static/ link is left untouched.
        ('/static/clean.png', '/static/clean.png'),
    )
    @ddt.unpack
    def test_normalize_static_links(self, url, expected):
        assert normalize_asset_url(url, COURSE_KEY) == expected

    @ddt.data(
        # Over-encoded asset-v1 link (serving form uses block/) -> portable.
        (
            '/asset-v1:Org+Course+Run+type@asset+block/D%252525C3%252525ADa.jpg',
            '/static/Día.jpg',
        ),
        # Already correctly-encoded asset-v1 link -> portable.
        (
            '/asset-v1:Org+Course+Run+type@asset+block@D%C3%ADa.jpg',
            '/static/Día.jpg',
        ),
    )
    @ddt.unpack
    def test_normalize_asset_v1_links(self, url, expected):
        assert normalize_asset_url(url, COURSE_KEY) == expected

    def test_asset_from_other_course_is_not_portablized(self):
        """An asset-v1 link from a different course is decoded but not reshaped."""
        url = '/asset-v1:Other+Course+Run+type@asset+block@D%C3%ADa.jpg'
        result = normalize_asset_url(url, COURSE_KEY)
        assert result == '/asset-v1:Other+Course+Run+type@asset+block@Día.jpg'

    def test_repair_text_reports_only_changed_urls(self):
        data = (
            '<img src="/static/D%2525C3%2525ADa.jpg"/>'
            "<img src='/static/clean.png'/>"
        )
        new_data, replacements = repair_text(data, COURSE_KEY)
        assert replacements == [('/static/D%2525C3%2525ADa.jpg', '/static/Día.jpg')]
        assert '/static/Día.jpg' in new_data
        assert '/static/clean.png' in new_data

    def test_repair_text_is_idempotent(self):
        data = '<img src="/static/D%252525C3%252525ADa.jpg"/>'
        once, _ = repair_text(data, COURSE_KEY)
        twice, replacements = repair_text(once, COURSE_KEY)
        assert twice == once
        assert replacements == []
