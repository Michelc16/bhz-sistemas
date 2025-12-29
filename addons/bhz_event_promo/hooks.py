"""Module hooks."""

from lxml import etree

from odoo import SUPERUSER_ID, api

import logging


_LOGGER = logging.getLogger(__name__)

SNIPPET_QWEB_ID = "s_guiabh_featured_carousel"
SNIPPET_DISPLAY_NAME = "GuiaBH - Carrossel de Destaques"
SNIPPET_THUMBNAIL = "/bhz_event_promo/static/description/featured_carousel.png"
SNIPPET_CATEGORY_LABEL = "GuiaBH"


def _find_container(root):
    """Return a node that can host snippet categories/items."""

    expressions = [
        ".//we-snippets",
        ".//*[contains(@class, 'o_we_snippet_categories')]",
        ".//*[contains(@class, 'o_panel_body')]",
    ]
    for expr in expressions:
        try:
            nodes = root.xpath(expr)
        except Exception:  # pragma: no cover - defensive
            nodes = []
        if nodes:
            return nodes[0]
    return root


def _ensure_category(container):
    """Return or create a category block for GuiaBH snippets."""

    for candidate in container.xpath(".//*[@data-name='%s']" % SNIPPET_CATEGORY_LABEL):
        if candidate.getparent() is not None:
            return candidate

    panel = etree.Element("div", {
        "class": "o_we_snippet_category",
        "data-name": SNIPPET_CATEGORY_LABEL,
        "data-icon": "fa fa-star",
    })
    header = etree.SubElement(panel, "div", {"class": "o_we_snippet_category_header"})
    etree.SubElement(header, "h3").text = SNIPPET_CATEGORY_LABEL
    etree.SubElement(panel, "div", {"class": "o_we_snippet_category_items"})
    container.append(panel)
    return panel


def _snippet_exists(root):
    xpath_expr = "//*[@data-snippet='%s']" % SNIPPET_QWEB_ID
    return bool(root.xpath(xpath_expr))


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    view = env.ref("website.snippets", raise_if_not_found=False)
    if not view:
        _LOGGER.warning("website.snippets not found; skipping GuiaBH snippet registration")
        return

    try:
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(view.arch_db.encode("utf-8"), parser=parser)
    except Exception:  # pragma: no cover - defensive
        _LOGGER.exception("Could not parse website.snippets arch for GuiaBH snippet")
        return

    if _snippet_exists(root):
        _LOGGER.info("GuiaBH snippet already registered in website.snippets")
        return

    container = _find_container(root)
    category = _ensure_category(container)
    items_node = category.xpath(".//*[contains(@class,'o_we_snippet_category_items')]")
    if items_node:
        items = items_node[0]
    else:
        items = etree.SubElement(category, "div", {"class": "o_we_snippet_category_items"})

    snippet_node = etree.Element(
        "we-snippet",
        {
            "data-name": SNIPPET_DISPLAY_NAME,
            "data-snippet": SNIPPET_QWEB_ID,
            "data-thumbnail": SNIPPET_THUMBNAIL,
            "data-categories": "GuiaBH,Events,Dynamic",
        },
    )
    items.append(snippet_node)
    view.write({"arch_db": etree.tostring(root, encoding="unicode")})
    _LOGGER.info("GuiaBH featured carousel snippet registered in website.snippets")
