{
    "name": "BHZ RMA",
    "summary": "Controle de RMA e estoque de produtos com defeito",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "BHZ Sistemas Desenvolvimento e Tecnologia LTDA",
    "website": "https://bhzsistemas.com.br",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/rma_sequence.xml",
        "data/rma_location.xml",
        "views/rma_menus.xml",
        "views/rma_views.xml",
    ],
    "installable": True,
    "application": True,
}
