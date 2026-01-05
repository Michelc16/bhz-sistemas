{
    "name": "BHZ - Agenda Futebol (Cruzeiro, Atlético-MG, América-MG)",
    "version": "1.0.0",
    "category": "Website",
    "summary": "Página no site com agenda de jogos dos times de BH (Cruzeiro, Atlético-MG e América-MG).",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["base", "website"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",

        "data/teams.xml",
        "data/website_menu.xml",

        "views/football_team_views.xml",
        "views/football_match_views.xml",
        "views/football_menu.xml",
        "views/res_config_settings_views.xml",
        "views/snippets/football_snippet.xml",
        "views/snippets/options.xml",
        "views_website/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "bhz_football_agenda/static/src/scss/football_snippet.scss",
            "bhz_football_agenda/static/src/js/guiabh_football_matches.js",
        ],
        "website.website_builder_assets": [
            "bhz_football_agenda/static/src/website_builder/**/*",
        ],
    },
    "application": True,
    "installable": True,
}
