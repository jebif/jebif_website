"""Template filters for the HTML written in the article editor (TinyMCE)."""
from urllib.parse import urlsplit

import nh3
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

# Tags and attributes produced by the TinyMCE plugins used in settings.TINYMCE_DEFAULT_CONFIG.
# Everything else (<script>, on* event handlers, javascript: links, ...) is removed.
ALLOWED_TAGS = nh3.ALLOWED_TAGS | {
    "iframe", "video", "audio", "source", "figure", "figcaption", "span", "u", "s",
}
ALLOWED_ATTRIBUTES = {
    tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()
}
for tag in ALLOWED_TAGS:
    ALLOWED_ATTRIBUTES.setdefault(tag, set()).update({"style", "class", "title", "lang"})
ALLOWED_ATTRIBUTES["a"].update({"href", "target"})
ALLOWED_ATTRIBUTES["img"].update({"src", "alt", "width", "height"})
ALLOWED_ATTRIBUTES["iframe"].update({"src", "width", "height", "allowfullscreen", "frameborder", "allow"})
ALLOWED_ATTRIBUTES["video"].update({"src", "width", "height", "controls", "poster"})
ALLOWED_ATTRIBUTES["audio"].update({"src", "controls"})
ALLOWED_ATTRIBUTES["source"].update({"src", "type"})
for tag in ("table", "td", "th", "tr", "col", "colgroup"):
    ALLOWED_ATTRIBUTES.setdefault(tag, set()).update({"border", "cellpadding", "cellspacing", "width", "height", "colspan", "rowspan"})


def _filter_attribute(tag, attribute, value):
    # <iframe> only from the hosts listed in settings.ARTICLE_IFRAME_HOSTS (videos)
    if tag == "iframe" and attribute == "src":
        url = urlsplit(value)
        if url.scheme != "https" or url.hostname not in settings.ARTICLE_IFRAME_HOSTS:
            return None
    return value


@register.filter(is_safe=True)
def sanitize_html(value):
    """Replacement for |safe on HTML written in the editor: keep the formatting,
    remove anything that could run a script in the visitor's browser."""
    if not value:
        return ""
    return mark_safe(nh3.clean(
        str(value),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        attribute_filter=_filter_attribute,
        link_rel="noopener noreferrer",
    ))
