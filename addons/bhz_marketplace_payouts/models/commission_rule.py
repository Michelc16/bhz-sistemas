# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzMarketplaceCommissionRule(models.Model):
    _name = "bhz.marketplace.commission.rule"
    _description = "Regra de comissão marketplace"
    _order = "sequence, id"

    name = fields.Char(required=True, default="Regra")
    seller_id = fields.Many2one("bhz.marketplace.seller", string="Seller específico")
    categ_id = fields.Many2one("product.category", string="Categoria específica")
    commission_rate = fields.Float(required=True, help="Percentual de comissão.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.model
    def match_rule(self, seller_id=None, categ_id=None):
        domain = [("active", "=", True)]
        if seller_id:
            domain.append(("seller_id", "=", seller_id))
        if categ_id:
            domain.append("|")
            domain.append(("categ_id", "=", categ_id))
            domain.append(("categ_id", "=", False))
        rule = self.search(domain, order="seller_id desc, categ_id desc, sequence asc", limit=1)
        return rule
