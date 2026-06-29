"""
Tests for the ``repair_asset_url_encoding`` management command helpers.

These cover the pure URL-normalization and asset-matching logic (no modulestore
required).
"""

import ddt
from django.test import SimpleTestCase
from opaque_keys.edx.keys import CourseKey

from cms.djangoapps.contentstore.management.commands.repair_asset_url_encoding import (
    AssetIndex,
    ascii_fold,
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
        ('Día.jpg', 'Da.jpg'),
        ('climática.svg.png', 'climtica.svg.png'),
        ('plain.png', 'plain.png'),
    )
    @ddt.unpack
    def test_ascii_fold(self, value, expected):
        assert ascii_fold(value) == expected

    @ddt.data(
        # Over-encoded /static/ links collapse to a single clean /static/ path.
        ('/static/D%252525C3%252525ADa.jpg', '/static/Día.jpg'),
        ('/static/D%25C3%25ADa.jpg', '/static/Día.jpg'),
        # A clean /static/ link is left untouched.
        ('/static/clean.png', '/static/clean.png'),
    )
    @ddt.unpack
    def test_normalize_static_links(self, url, expected):
        new_url, status = normalize_asset_url(url, COURSE_KEY)
        assert new_url == expected
        assert status is None

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
        new_url, status = normalize_asset_url(url, COURSE_KEY)
        assert new_url == expected
        assert status is None

    def test_asset_from_other_course_is_not_portablized(self):
        """An asset-v1 link from a different course is decoded but not reshaped."""
        url = '/asset-v1:Other+Course+Run+type@asset+block@D%C3%ADa.jpg'
        new_url, status = normalize_asset_url(url, COURSE_KEY)
        assert new_url == '/asset-v1:Other+Course+Run+type@asset+block@Día.jpg'
        assert status is None

    def test_repair_text_reports_only_changed_urls(self):
        data = (
            '<img src="/static/D%2525C3%2525ADa.jpg"/>'
            "<img src='/static/clean.png'/>"
        )
        new_data, replacements, warnings = repair_text(data, COURSE_KEY)
        assert replacements == [('/static/D%2525C3%2525ADa.jpg', '/static/Día.jpg')]
        assert warnings == []
        assert '/static/Día.jpg' in new_data
        assert '/static/clean.png' in new_data

    def test_repair_text_is_idempotent(self):
        data = '<img src="/static/D%252525C3%252525ADa.jpg"/>'
        once, _, _ = repair_text(data, COURSE_KEY)
        twice, replacements, warnings = repair_text(once, COURSE_KEY)
        assert twice == once
        assert replacements == []
        assert warnings == []


@ddt.ddt
class AssetIndexTest(SimpleTestCase):
    """Unit tests for matching broken references against real assets."""

    def setUp(self):
        super().setUp()
        self.index = AssetIndex([
            'Día_1.jpg',
            'Logo_Justicia_climática_01.svg.png',
            'plain.png',
        ])

    @ddt.data(
        ('plain.png', ('ok', 'plain.png')),
        ('Día_1.jpg', ('ok', 'Día_1.jpg')),
        # Dropped-character reference resolves to the accented real asset.
        ('Logo_Justicia_climtica_01.svg.png', ('matched', 'Logo_Justicia_climática_01.svg.png')),
        ('Da_1.jpg', ('matched', 'Día_1.jpg')),
        ('does_not_exist.png', ('unmatched', None)),
    )
    @ddt.unpack
    def test_resolve(self, filename, expected):
        assert self.index.resolve(filename) == expected

    def test_resolve_ambiguous(self):
        # 'Día.png' and 'Dáa.png' both fold to 'Da.png' (accents are dropped,
        # not transliterated), so a 'Da.png' reference can't be disambiguated.
        index = AssetIndex(['Día.png', 'Dáa.png'])
        assert index.resolve('Da.png') == ('ambiguous', None)

    def test_normalize_repoints_dropped_character_link(self):
        url = '/static/Logo_Justicia_climtica_01.svg.png'
        new_url, status = normalize_asset_url(url, COURSE_KEY, self.index)
        assert new_url == '/static/Logo_Justicia_climática_01.svg.png'
        assert status == 'matched'

    def test_normalize_existing_asset_is_untouched(self):
        url = '/static/plain.png'
        new_url, status = normalize_asset_url(url, COURSE_KEY, self.index)
        assert new_url == '/static/plain.png'
        assert status is None

    def test_normalize_unmatched_link_warns_but_keeps_decoded(self):
        url = '/static/totally_missing.png'
        new_url, status = normalize_asset_url(url, COURSE_KEY, self.index)
        assert new_url == '/static/totally_missing.png'
        assert status == 'unmatched'

    def test_repair_text_with_index_repoints_and_warns(self):
        data = (
            '<img src="/static/Logo_Justicia_climtica_01.svg.png"/>'
            '<img src="/static/totally_missing.png"/>'
        )
        new_data, replacements, warnings = repair_text(data, COURSE_KEY, self.index)
        assert replacements == [
            ('/static/Logo_Justicia_climtica_01.svg.png', '/static/Logo_Justicia_climática_01.svg.png'),
        ]
        assert warnings == [('/static/totally_missing.png', 'unmatched')]
        assert '/static/Logo_Justicia_climática_01.svg.png' in new_data
