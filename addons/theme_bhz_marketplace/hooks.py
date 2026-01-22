# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(env_or_cr, registry=None):
    """Apply the theme and create basic pages/menus for the marketplace website only."""
    if registry is None:
        # Odoo 17+/19 may pass env directly
        env = env_or_cr.sudo() if hasattr(env_or_cr, "sudo") else env_or_cr
    else:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    Website = env["website"]

    # Isolated website lookup/creation (prefer existing current website)
    site = Website.get_current_website()
    if not site:
        site = Website.search([], limit=1)
    if not site:
        site = Website.create({"name": "BHZ Marketplace"})

    # Apply theme only to this website
    if hasattr(site, "_set_theme"):
        try:
            site.with_context(install_theme=True)._set_theme("theme_bhz_marketplace")
        except Exception:
            # avoid blocking install if theme application fails
            pass

    # Pages to create if missing (attached to marketplace website)
    pages_spec = [
        ("/", "Marketplace Home", "theme_bhz_marketplace.page_home"),
        ("/marketplace/shop", "Marketplace Shop", "theme_bhz_marketplace.page_shop"),
        ("/marketplace/product", "Marketplace Produto", "theme_bhz_marketplace.page_product"),
        ("/marketplace/seller", "Marketplace Loja do Vendedor", "theme_bhz_marketplace.page_seller"),
        ("/marketplace/dashboard", "Dashboard do Vendedor", "theme_bhz_marketplace.page_dashboard"),
        ("/marketplace/search", "Busca Marketplace", "theme_bhz_marketplace.page_search"),
        ("/marketplace/categories", "Categorias Marketplace", "theme_bhz_marketplace.page_categories"),
        ("/marketplace/how-it-works", "Como funciona", "theme_bhz_marketplace.page_how_it_works"),
        ("/marketplace/become-a-seller", "Seja um vendedor", "theme_bhz_marketplace.page_become_seller"),
    ]

    Page = env["website.page"]
    home_page = False
    for url, name, view_xmlid in pages_spec:
        if not Page.search([("url", "=", url), ("website_id", "=", site.id)], limit=1):
            page = Page.create(
                {
                    "url": url,
                    "name": name,
                    "website_id": site.id,
                    "view_id": env.ref(view_xmlid).id,
                }
            )
        else:
            page = Page.search([("url", "=", url), ("website_id", "=", site.id)], limit=1)
            page.write({"name": name, "view_id": env.ref(view_xmlid).id})
        if url == "/":
            home_page = page

    if home_page:
        site.write({"homepage_id": home_page.id})

    # Menus (main + children) only for this site
    Menu = env["website.menu"]
    main_menu = Menu.search([("website_id", "=", site.id), ("url", "=", "/")], limit=1)
    if not main_menu:
        main_menu = Menu.create({"name": "Marketplace", "url": "/", "website_id": site.id, "sequence": 5})
    else:
        main_menu.write({"name": "Marketplace", "url": "/", "website_id": site.id})

    def _ensure_menu(name, url, sequence):
        if not Menu.search([("website_id", "=", site.id), ("parent_id", "=", main_menu.id), ("url", "=", url)], limit=1):
            Menu.create(
                {"name": name, "url": url, "website_id": site.id, "parent_id": main_menu.id, "sequence": sequence}
            )

    _ensure_menu("Categorias", "/marketplace/categories", 10)
    _ensure_menu("Ofertas", "/marketplace/shop", 20)
    _ensure_menu("Lojas", "/marketplace/seller", 30)
    _ensure_menu("Seja um vendedor", "/marketplace/become-a-seller", 40)
    _ensure_menu("Ajuda", "/marketplace/how-it-works", 50)
