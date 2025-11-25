{
    "name": "BHZ Branding (DOM)",
    "version": "19.0.1.0.0",
    "summary": "Branding BHZ SISTEMAS - title, favicon, logo and UI tweaks",
    "category": "Tools",
    "author": "BHZ SISTEMAS",
    "website": "https://www.bhzsistemas.com.br",
    "license": "LGPL-3",
    "depends": ["web", "website"],    
    "data": [],
    "assets": {
        "web.assets_backend": [
            "bhz_branding_dom/static/src/scss/bhz_branding.scss",
            "bhz_branding_dom/static/src/js/bhz_branding.js",
        ],
        "web.assets_frontend": [
            "bhz_branding_dom/static/src/scss/bhz_branding.scss",
            "bhz_branding_dom/static/src/js/bhz_branding.js",
        ],
    },
    "installable": True,
    "application": False,
}
