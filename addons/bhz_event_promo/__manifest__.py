{
    "name": "GuiaBH - Eventos (Agenda + Terceiros + Botão custom)",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Agenda de eventos com suporte a eventos de terceiros, link externo e botão personalizável.",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["base", "website", "event", "website_event", "event_sale"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/event_views.xml",
        "views/website_menu.xml",
        "views/templates.xml",
        "views/announced_events_snippet.xml",
        "views/featured_carousel_snippet.xml",
        "views/snippets/options.xml",
        "views/bhz_event_import_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "bhz_event_promo/static/src/scss/guiabh_event.scss",
            "bhz_event_promo/static/src/js/guiabh_featured_carousel.js",
        ],
    },
    "installable": True,
    "application": False,
}
