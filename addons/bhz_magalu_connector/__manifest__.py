{
    "name": "BHZ Magalu Connector",
    "summary": "Integração BHZ Magalu plug and play (Odoo 19)",
    "version": "19.0.1.0.0",
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "stock",
        "product",
        "mail",
    ],
    "data": [
<<<<<<< HEAD
        "security/ir.model.access.csv",        
=======
        "security/ir.model.access.csv",
        "data/magalu_params.xml",
>>>>>>> 03b37ce4a9a7adc5e87ebf118e772d1eb2f49447
        "data/magalu_cron.xml",
        "views/magalu_config_views.xml",
        "views/magalu_product_views.xml",
        "views/magalu_order_views.xml",
    ],
    "application": True,
    "installable": True,
    "pre_init_hook": "pre_init_set_magalu_client",
}
