{
    "name": "BHZ WhatsApp Omni (Starter + Business)",
    "summary": "Atendimento WhatsApp: Starter (QR) + Business (Cloud API) com inbox, IA e anti-abuso",
    "version": "19.0.1.0.0",
    "category": "Tools/Communication",
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "assets": {
        "web.assets_backend": [
            "bhz_whatsapp_omni/static/src/js/wa_inbox.js",
            "bhz_whatsapp_omni/static/src/xml/wa_inbox.xml",
            "bhz_whatsapp_omni/static/src/scss/wa_inbox.scss",
        ],
    },
    "post_init_hook": "post_init_set_starter_defaults",
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/wa_session_views.xml",
        "views/wa_account_views.xml",
        "views/wa_message_views.xml",
        "views/wa_template_views.xml",
        "views/res_config_views.xml",
        "views/wa_menus.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
    "description": """
BHZ WhatsApp Omni
-----------------
• Starter (QR) – conexão estilo WhatsApp Web via Baileys, limites anti-abuso, sem broadcast.
• Business (Cloud API) – integração oficial Meta, webhooks e templates aprovados.
• Inbox unificada, IA atendente via webhook e quiet hours configuráveis.
""",
}
