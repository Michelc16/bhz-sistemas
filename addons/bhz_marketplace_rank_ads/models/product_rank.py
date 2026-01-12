# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bhz_rank_score = fields.Float("Marketplace Rank", compute="_compute_rank", store=True)

    @api.depends("bhz_seller_id", "list_price")
    def _compute_rank(self):
        for prod in self:
            score = 10.0
            if prod.bhz_seller_id:
                rep = self.env["bhz.seller.reputation"].search([("seller_id", "=", prod.bhz_seller_id.id)], limit=1)
                score += rep.score if rep else 0
                ads = self.env["bhz.product.ads"].search([("product_tmpl_id", "=", prod.id), ("active", "=", True)], limit=1)
                if ads and ads.budget > ads.spent:
                    score += (ads.boost or 1.0) * 10
            # leve ajuste inverso do preço: mais barato => +5
            if prod.list_price:
                score += max(0, 5 - (prod.list_price / 10000.0))
            prod.bhz_rank_score = score
