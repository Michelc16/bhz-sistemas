{
    "name": "BHZ Dealer Website",
    "version": "19.0.1.0.1",
    "category": "Website",
    "summary": "Site moderno para concessionárias: estoque, detalhe do carro, filtros e captação de leads.",
    "description": "Aplicativo BHZ Dealer para publicar estoque de carros, páginas de detalhe e captação de leads no site.",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["website", "crm", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/car_views.xml",
        "views/config_views.xml",
        "views/dealer_menu.xml",
        "views/website_templates.xml",
        "views/website_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "bhz_dealer_website/static/src/scss/dealer.scss",
            "bhz_dealer_website/static/src/js/dealer.js",
        ],
    },
    "demo": [
        "data/demo.xml",
    ],
    "application": True,
    "installable": True,
}
