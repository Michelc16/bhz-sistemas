{
    "name": "BHZ Marketplace Returns & Disputes",
    "version": "19.0.1.0.0",
    "category": "Website/Marketplace",
    "summary": "Devoluções/disputas com sellers, portal e integração de refund no ledger.",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["bhz_marketplace_core", "bhz_marketplace_payouts", "sale_management", "portal", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "views/menu.xml",
        "views/return_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
}
