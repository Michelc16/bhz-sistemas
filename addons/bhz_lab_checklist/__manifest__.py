{
    "name": "BHZ Laboratório - Checklist de Equipamentos",
    "summary": "Gera checklist para computadores e notebooks em pedidos de venda",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "BHZ Sistemas",
    "website": "https://bhzsistemas.com.br",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/lab_checklist_template_data.xml",
        "views/lab_checklist_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
    ],
    "application": True,
    "installable": True,
}
