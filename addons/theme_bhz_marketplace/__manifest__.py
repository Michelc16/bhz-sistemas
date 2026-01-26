# -*- coding: utf-8 -*-
{
    "name": "Theme BHZ Marketplace",
    "summary": "Tema isolado para o marketplace BHZ (home, loja, produto, vendedor, dashboard).",
    "version": "19.0.1.0.0",
    "category": "Theme/Marketplace",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "website": "https://bhzsistemas.com.br",
    "depends": [
        "website",
        "website_sale",
        "bhz_marketplace_core",
    ],
 
    "data": [
        "data/website.xml",
        "data/menus.xml",
        
    ],
    
    "qweb": [
        "views/layouts.xml",
        "views/home.xml",
        "views/shop.xml",
        "views/product.xml",
        "views/seller.xml",
        "views/dashboard.xml",
        "views/static_pages.xml",
    ],

    "assets": {
        "web.assets_frontend": [
            "theme_bhz_marketplace/static/src/css/marketplace.css",
        ],
    },

    "installable": True,
    "application": False,
}
