# -*- coding: utf-8 -*-
{
    "name": "Theme BHZ Marketplace",
    "summary": "Tema do marketplace BHZ (home, shop, product, seller, dashboard).",
    "version": "19.0.1.0.0",
    "category": "Website/Theme",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "website": "https://bhzsistemas.com.br",
    "depends": [
        "website",
        "website_sale",
        "portal",
        "bhz_marketplace_core",
    ],

    # ✅ IMPORTANTE: tudo em "data" e em ORDEM
    "data": [
        # 1) views (criam ir.ui.view / templates)
        "views/layouts.xml",
        "views/home.xml",
        "views/shop.xml",
        "views/product.xml",
        "views/seller.xml",
        "views/dashboard.xml",
        "views/static_pages.xml",

        # 2) menus e páginas (referenciam os views acima)
        "data/menus.xml",
        "data/pages.xml",
    ],

    "assets": {
        "web.assets_frontend": [
            "theme_bhz_marketplace/static/src/css/marketplace.css",
        ],
    },

    "installable": True,
    "application": False,
}
