# -*- coding: utf-8 -*-
{
    "name": "GuiaBH - Eventos (Agenda + Terceiros + Botão custom)",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Agenda de eventos com suporte a eventos de terceiros, link externo e botão personalizável.",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["website_event", "event_sale"],  # event_sale opcional, mas útil
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/event_views.xml",
        "views/website_menu.xml",
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "guiabh_event_promo/static/src/scss/guiabh_event.scss",
        ],
    },
    "installable": True,
    "application": False,
}
