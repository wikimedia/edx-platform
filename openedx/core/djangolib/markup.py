"""
Utilities for use in Mako markup.
"""


import markupsafe
import bleach
import re
from lxml.html.clean import Cleaner
from mako.filters import decode

# Text() can be used to declare a string as plain text, as HTML() is used
# for HTML.  It simply wraps markupsafe's escape, which will HTML-escape if
# it isn't already escaped.
Text = markupsafe.escape                        # pylint: disable=invalid-name


class HTMLCleaner(Cleaner):
    """
    HTMLCleaner extends lxml.html.clean.Cleaner to sanitize HTML content while preserving
    valid URLs and removing unsafe JavaScript links.
    """
    def _remove_javascript_link(self, link: str):
        """
        Overrides the parent class's method to preserve valid URLs.

        This method uses a regular expression to identify valid URLs that start with 'http', 'https',
        'ftp', or 'file' schemes. If the link is a valid URL, it is returned unchanged. Otherwise,
        the parent class's method is used to remove the JavaScript link.

        Args:
            link (str): The hyperlink (href attribute value) to be checked and potentially sanitized.

        Returns:
            str: The original link or empty string.

        Examples:
            Valid URLs:
                'https://www.example.com/javascript:something'
                'file://localhost/path/to/file'
            Invalid URLs:
                'javascript:alert("hello")'
                'javascript:alert("hello") https://www.example.com/page'
        """
        is_url = re.compile(r"^(?:https?|ftp|file)://", re.I).search(link.strip())
        if is_url:
            return link
        return super()._remove_javascript_link(link)
        

def HTML(html):                                 # pylint: disable=invalid-name
    """
    Mark a string as already HTML, so that it won't be escaped before output.

    Use this function when formatting HTML into other strings.  It must be
    used in conjunction with ``Text()``, and both ``HTML()`` and ``Text()``
    must be closed before any calls to ``format()``::

        <%page expression_filter="h"/>
        <%!
        from django.utils.translation import ugettext as _

        from openedx.core.djangolib.markup import HTML, Text
        %>
        ${Text(_("Write & send {start}email{end}")).format(
            start=HTML("<a href='mailto:{}'>").format(user.email),
            end=HTML("</a>"),
        )}

    """
    return markupsafe.Markup(html)


def strip_all_tags_but_br(string_to_strip):
    """
    Strips all tags from a string except <br/> and marks as HTML.

    Usage:
        <%page expression_filter="h"/>
        <%!
        from openedx.core.djangolib.markup import strip_all_tags_but_br
        %>
        ${accomplishment_course_title | n, strip_all_tags_but_br}
    """

    if string_to_strip is None:
        string_to_strip = ""

    string_to_strip = decode.utf8(string_to_strip)
    string_to_strip = bleach.clean(string_to_strip, tags=['br'], strip=True)

    return HTML(string_to_strip)


def clean_dangerous_html(html):
    """
    Mark a string as already HTML and remove unsafe tags, so that it won't be escaped before output.
        Usage:
        <%page expression_filter="h"/>
        <%!
        from openedx.core.djangolib.markup import clean_dangerous_html
        %>
        ${course_details.overview | n, clean_dangerous_html}
    """
    if not html:
        return html
    cleaner = HTMLCleaner(style=True, inline_style=False, safe_attrs_only=False)
    html = cleaner.clean_html(html)
    return HTML(html)
