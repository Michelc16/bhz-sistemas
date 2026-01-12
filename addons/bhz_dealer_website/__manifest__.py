{
    "name": "BHZ Dealer Website",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Site moderno para concessionárias: estoque, detalhe do carro, filtros e captação de leads.",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["website", "website_sale", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/demo.xml",
        "views/car_views.xml",
        "views/website_menus.xml",
        "views/website_templates.xml",
        "views/website_pages.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "bhz_dealer_website/static/src/scss/dealer.scss",
            "bhz_dealer_website/static/src/js/dealer.js",
        ],
    },
    "application": True,
    "installable": True,
}
