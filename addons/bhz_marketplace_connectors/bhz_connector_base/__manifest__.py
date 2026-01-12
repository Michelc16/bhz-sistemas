{
    "name": "BHZ Connector Base",
    "version": "19.0.1.0.0",
    "category": "Website/Marketplace",
    "summary": "Base para conectores ERP (Tiny, Bling, Omie)",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["bhz_marketplace_core", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/connector_account_views.xml",
        "views/connector_job_views.xml",
    ],
    "installable": True,
}
