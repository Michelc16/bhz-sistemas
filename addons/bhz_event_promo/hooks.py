"""Post-init hooks to register website snippets safely."""

import logging

from lxml import etree

from odoo import SUPERUSER_ID, api


_LOGGER = logging.getLogger(__name__)

SNIPPET_ID = "s_guiabh_featured_carousel"
SNIPPET_DISPLAY_NAME = "GuiaBH - Carrossel de Destaques"
SNIPPET_THUMBNAIL = "/bhz_event_promo/static/description/featured_carousel.png"


def _load_arch(view):
    parser = etree.XMLParser(remove_blank_text=False)
    return etree.fromstring(view.arch_db.encode("utf-8"), parser=parser)


def _preview_exists(root):
    return bool(root.xpath(f"//*[@data-snippet-id='{SNIPPET_ID}']"))


def _build_preview():
    markup = f"""
    <div class="o_snippet_preview_wrap position-relative"
         data-snippet-id="{SNIPPET_ID}"
         data-name="{SNIPPET_DISPLAY_NAME}"
         tabindex="0"
         role="button"
         aria-label="Eventos">
        <div class="o_snippet_preview o_snippet_preview_carousel">
            <img class="o_snippet_thumbnail"
                 src="{SNIPPET_THUMBNAIL}"
                 alt="{SNIPPET_DISPLAY_NAME}"/>
        </div>
    </div>
    """
    return etree.fromstring(markup)


def _find_anchor(root):
    anchor = root.xpath("//div[@data-snippet-id='s_events_picture']")
    if anchor:
        return anchor[0]
    return None


def _insert_preview(root):
    if _preview_exists(root):
        return False

    anchor = _find_anchor(root)
    preview = _build_preview()
    if anchor is not None and anchor.getparent() is not None:
        anchor.addnext(preview)
    else:
        # fallback: append at the end of the root
        root.append(preview)
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

    if not _insert_preview(root):
        _LOGGER.info("GuiaBH snippet already registered in website.snippets")
        return

    view.write({"arch_db": etree.tostring(root, encoding="unicode")})
    _LOGGER.info("GuiaBH snippet successfully registered in website.snippets")
