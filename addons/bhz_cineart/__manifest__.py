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
        "data/ir_cron.xml",
        "views/cineart_movie_views.xml",
        "views/cineart_menus.xml",
        "views_website/cineart_templates.xml",
    ],
    "installable": True,
    "application": False,
}
