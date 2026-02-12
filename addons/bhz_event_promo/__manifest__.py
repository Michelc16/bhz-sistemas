{
    "name": "GuiaBH - Eventos (Agenda + Terceiros + Botão custom)",
    "version": "19.0.1.0.1",
    "category": "Website",
    "summary": "Agenda de eventos com suporte a eventos de terceiros, link externo e botão personalizável.",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["base", "website", "event", "website_event", "event_sale"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "data/portalbh_carnaval_cron.xml",
        "views/event_views.xml",
        "views/website_menu.xml",
        "views/templates.xml",
        "views/announced_events_snippet.xml",
        "views/featured_carousel_snippet.xml",
        "views/snippets/options.xml",
        "views/res_config_settings_view.xml",
        "views/bhz_event_import_views.xml",
        "views/portalbh_carnaval_import_views.xml",
        "views/portalbh_carnaval_job_views.xml",
    ],
    # Frontend assets must live in web.assets_frontend so they load on all public pages
    # (blog, home, landing, etc.). Editor assets remain in website.assets_editor.
    "assets": {
        "web.assets_frontend": [
            "bhz_event_promo/static/src/scss/guiabh_event.scss",
            "bhz_event_promo/static/src/js/guiabh_announced_events.js",
            "bhz_event_promo/static/src/js/guiabh_featured_carousel.js",
        ],
        # Editor/builder assets: kept in the new website builder bundle to avoid
        # loading them on every backend page and to make snippet options available
        # in the visual editor.
        "website.website_builder_assets": [
            "bhz_event_promo/static/src/website_builder/**/*",
        ],
        "website.assets_editor": [],
    },
    "installable": True,
    "application": False,
}
