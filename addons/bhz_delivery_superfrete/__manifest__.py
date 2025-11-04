{
    "name": "BHZ Delivery SuperFrete",
    "summary": "Cotação de fretes via SuperFrete nos pedidos de venda/entrega.",
    "version": "19.0.1.0.0",
    "author": "BHZ Sistemas",
    "website": "https://bhz-sistemas.odoo.com/odoo",
    "category": "Inventory/Delivery",
    "license": "LGPL-3",
    "depends": ["delivery", "sale_management", "stock", "contacts"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "views/superfrete_views.xml",
        "views/delivery_carrier_views.xml",
    ],
    "installable": True,
    "application": False,
}
