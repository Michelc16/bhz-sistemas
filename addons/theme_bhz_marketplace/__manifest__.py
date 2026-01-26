# -*- coding: utf-8 -*-
{
    "name": "BHZ Marketplace Theme",
    "summary": "Tema do BHZ Marketplace",
    "version": "19.0.1.0.0",
    "category": "Website/Theme",
    "license": "LGPL-3",
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "depends": [
        "website",
        # importante: tema depende do core do marketplace
        "bhz_marketplace_core",
    ],
    "data": [
        # Views / templates do website (páginas)
        "views/layouts.xml",
        "views/home.xml",
        "views/shop.xml",
        "views/product.xml",
        "views/seller.xml",
        "views/dashboard.xml",
        "views/static_pages.xml",
    ],
    # NÃO coloque essas páginas em "qweb"
    # "qweb": [],  # <- não usar no tema (deixa fora)
    "assets": {
        "web.assets_frontend": [
            # se você tiver scss/js do tema, inclua aqui
            # "theme_bhz_marketplace/static/src/scss/theme.scss",
            # "theme_bhz_marketplace/static/src/js/theme.js",
        ],
    },
    "installable": True,
    "application": False,
}
