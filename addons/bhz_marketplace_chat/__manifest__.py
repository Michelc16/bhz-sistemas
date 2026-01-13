{
    "name": "BHZ Marketplace Chat (Q&A)",
    "version": "19.0.1.0.0",
    "category": "Website/Marketplace",
    "summary": "Perguntas e respostas de produtos para sellers",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["bhz_marketplace_core", "portal", "website", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "views/question_views.xml",
        "views/menu.xml",
        "views/portal_templates.xml",
        "views/website_templates.xml",
    ],
    "installable": True,
}
