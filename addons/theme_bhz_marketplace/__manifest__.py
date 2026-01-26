# -*- coding: utf-8 -*-
{
    "name": "Mercado BHZ",
    "summary": "Tema do marketplace BHZ (home, shop, product, seller, dashboard).",
    "version": "19.0.1.0.0",
    "category": "Theme",
    "license": "LGPL-3",
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "depends": [
        "website",
        "website_sale",
        "portal",
        "bhz_marketplace_core",
    ],
    "data": [
        # ✅ 1) Views primeiro (cria ir.ui.view e os xmlids page_*)
        "views/layouts.xml",
        "views/home.xml",
        "views/shop.xml",
        "views/product.xml",
        "views/seller.xml",
        "views/dashboard.xml",
        "views/static_pages.xml",

        # ✅ 2) Dados depois (usam refs dos templates acima)
        "data/pages.xml",
        "data/menus.xml",
        "data/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "theme_bhz_marketplace/static/src/css/marketplace.css",
            "theme_bhz_marketplace/static/src/js/marketplace.js",
        ],
    },
    # ✅ NÃO usar hook no tema (evita sumir/quebrar no wizard)
    # "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
