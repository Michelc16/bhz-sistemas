{
    "name": "BHZ Branding Oficial",
    "summary": "Substitui marca visual padrão pela identidade BHZ SISTEMAS (versão segura para Odoo.sh/Enterprise)",
    "version": "19.0.1.0.0",
    "author": "BHZ SISTEMAS",
    "website": "https://www.bhzsistemas.com.br",
    "category": "Tools",
    "license": "LGPL-3",
    "depends": [
        "web",
        "website",
        "website_sale",
    ],
    "data": [
        "views/webclient_templates.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # se quiser pôr CSS depois:
            # "bhz_branding_official/static/src/scss/bhz_branding.scss",
        ],
        "web.assets_frontend": [
            # idem
        ],
    },
    "installable": True,
    "application": False,
}
