{
    "name": "BHZ Marketplace Shipping",
    "version": "19.0.1.0.0",
    "category": "Website/Marketplace",
    "summary": "Envios por seller com tracking e portal.",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["bhz_marketplace_core", "sale_management", "portal"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "views/menu.xml",
        "views/shipment_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
}
