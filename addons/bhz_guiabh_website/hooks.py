# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def post_init_hook(env_or_cr, registry=None):
    """Ensure the theme home page exists and is published."""
    if registry is None:
        env = env_or_cr.sudo() if hasattr(env_or_cr, "sudo") else env_or_cr
    else:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})

    Website = env["website"]
    Page = env["website.page"]

    site = Website.get_current_website() or Website.search([], limit=1)
    if not site:
        return

    view = env.ref("bhz_guiabh_website.theme_guiabh_website_homepage", raise_if_not_found=False)
    if not view:
        return

    page = Page.search([("url", "=", "/"), ("website_id", "=", site.id)], limit=1)
    values = {
        "url": "/",
        "name": "GuiaBH Home",
        "website_id": site.id,
        "view_id": view.id,
        "website_published": True,
    }
    if page:
        page.write(values)
    else:
        Page.create(values)
