{
    "name": "GuiaBH - Cineart (Página exclusiva + sincronização de filmes)",
    "version": "1.0.0",
    "category": "Website",
    "summary": "Página /cineart com Em Cartaz, Em Breve e Estreias da Semana (sincroniza do site do Cineart).",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["base", "website"],
    "data": [
        "security/ir.model.access.csv",
        "data/cineart_category_data.xml",
        "data/ir_cron.xml",
        "views/cineart_movie_views.xml",
        "views/cineart_menus.xml",
        "views/cineart_snippet.xml",
        "views/snippets/options.xml",
        "views_website/cineart_templates.xml",
        "views_website/cineart_website_menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "bhz_cineart/static/src/scss/cineart_snippet.scss",
            "bhz_cineart/static/src/js/guiabh_cineart_movies.js",
        ],
        "website.website_builder_assets": [
            "bhz_cineart/static/src/website_builder/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
