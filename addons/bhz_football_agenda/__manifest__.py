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
        "views_website/website_templates.xml",
    ],
    "application": True,
    "installable": True,
}
