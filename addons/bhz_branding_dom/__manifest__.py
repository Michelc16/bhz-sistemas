# bhz_branding_dom/__manifest__.py
{
    "name": "BHZ Branding (DOM)",
    "summary": "Aplica marca BHZ SISTEMAS via DOM/JS sem herdar views de branding da Odoo",
    "version": "19.0.1.0.0",
    "author": "BHZ SISTEMAS",
    "website": "https://www.bhzsistemas.com.br",
    "license": "LGPL-3",
    "category": "Tools",
    "depends": ["web", "website"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "bhz_branding_dom/static/src/js/bhz_backend.js",
        ],
        "web.assets_frontend": [
            "bhz_branding_dom/static/src/js/bhz_website.js",
        ],
    },
    "installable": True,
    "application": False,
}
