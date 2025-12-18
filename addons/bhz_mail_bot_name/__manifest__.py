{
    "name": "Assistente BHZ (Bot Odoo)",
    "summary": "Renomeia OdooBot, troca avatar, mensagens e tema do chat para BHZ.",
    "version": "19.0.1.0.0",
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "license": "LGPL-3",
    "category": "Discuss",
    "depends": ["mail_bot", "mail", "web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "bhz_mail_bot_name/static/src/scss/bhz_assistente_bhz.scss",
        ],
    },    
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
