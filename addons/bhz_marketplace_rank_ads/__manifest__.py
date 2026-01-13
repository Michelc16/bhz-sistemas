{
    "name": "BHZ Marketplace Rank & Ads",
    "version": "19.0.1.0.0",
    "category": "Website/Marketplace",
    "summary": "Reputação do seller e anúncios impulsionados para ranking de produtos",
    "author": "BHZ Sistemas",
    "license": "LGPL-3",
    "depends": ["bhz_marketplace_core", "website_sale"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/reputation_views.xml",
        "views/product_ads_views.xml",
        "views/product_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
}
