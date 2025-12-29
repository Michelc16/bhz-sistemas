"""Post-init hooks to register website snippets safely."""

import logging

from lxml import etree

from odoo import SUPERUSER_ID, api


_LOGGER = logging.getLogger(__name__)

SNIPPET_ID = "s_guiabh_featured_carousel"
SNIPPET_DISPLAY_NAME = "GuiaBH - Carrossel de Destaques"
SNIPPET_THUMBNAIL = "/bhz_event_promo/static/description/featured_carousel.png"
SNIPPET_CATEGORIES = "events,GuiaBH"


def _load_arch(view):
    parser = etree.XMLParser(remove_blank_text=False)
    return etree.fromstring(view.arch_db.encode("utf-8"), parser=parser)


def _snippet_exists(root):
    return bool(root.xpath(f".//we-snippet[@data-snippet='{SNIPPET_ID}']"))


def _build_we_snippet():
    return etree.Element(
        "we-snippet",
        {
            "data-name": SNIPPET_DISPLAY_NAME,
            "data-snippet": SNIPPET_ID,
            "data-thumbnail": SNIPPET_THUMBNAIL,
            "data-categories": SNIPPET_CATEGORIES,
        },
    )


def _find_anchor(root):
    snippets = root.xpath(".//we-snippet")
    if not snippets:
        return None
    for node in snippets:
        categories = (node.get("data-categories") or "").lower()
        snippet_name = node.get("data-snippet") or ""
        if "event" in categories or snippet_name.startswith("s_events"):
            return node
    return snippets[-1]


def _insert_snippet(root):
    if _snippet_exists(root):
        return False

    anchor = _find_anchor(root)
    new_snippet = _build_we_snippet()
    if anchor is not None and anchor.getparent() is not None:
        anchor.addnext(new_snippet)
    else:
        root.append(new_snippet)
    return True


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    view = env.ref("website.snippets", raise_if_not_found=False)
    if not view:
        _LOGGER.warning("website.snippets view not found; skipping GuiaBH snippet registration")
        return

    try:
        root = _load_arch(view)
    except Exception:
        _LOGGER.exception("Unable to parse website.snippets when registering GuiaBH snippet")
        return

    if not _insert_snippet(root):
        _LOGGER.info("GuiaBH snippet already registered in website.snippets")
        return

    view.write({"arch_db": etree.tostring(root, encoding="unicode")})
    _LOGGER.info("GuiaBH snippet successfully registered in website.snippets")
