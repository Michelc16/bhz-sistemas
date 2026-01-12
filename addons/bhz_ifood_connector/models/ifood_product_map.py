# -*- coding: utf-8 -*-
from odoo import fields, models

class BhzIFoodProductMap(models.Model):
    _name = "bhz.ifood.product.map"
    _description = "Mapa Produto iFood -> Odoo"
    _rec_name = "ifood_sku"
    _sql_constraints = [
        ("uniq_ifood_sku_company", "unique(ifood_sku, company_id)", "SKU iFood já mapeado para esta empresa."),
    ]

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    account_id = fields.Many2one("bhz.ifood.account", required=True, ondelete="cascade")

    ifood_sku = fields.Char(required=True, index=True)
    ifood_name = fields.Char()
    product_id = fields.Many2one("product.product", required=True, ondelete="restrict")
