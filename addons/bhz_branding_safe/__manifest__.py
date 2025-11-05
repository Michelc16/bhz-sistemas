{
    "name": "BHZ Branding (Safe)",
    "summary": "Personalização visual BHZ SISTEMAS com co-branding Odoo",
    "version": "19.0.1.0.0",
    "author": "BHZ SISTEMAS",
    "website": "https://www.bhzsistemas.com.br",
    "category": "Tools",
    "license": "LGPL-3",
    "depends": ["web", "website", "portal"],
    "data": [
        "views/webclient_templates.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "bhz_branding_safe/static/src/scss/bhz_branding.scss",
        ],
        "web.assets_frontend": [
            "bhz_branding_safe/static/src/scss/bhz_branding.scss",
        ],
    },
    "installable": True,
    "application": False,
}
