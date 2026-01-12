# -*- coding: utf-8 -*-
from odoo import fields, models


class BhzProductAds(models.Model):
    _name = "bhz.product.ads"
    _description = "Anúncios impulsionados"
    _order = "id desc"

    product_tmpl_id = fields.Many2one("product.template", required=True, ondelete="cascade")
    seller_id = fields.Many2one(related="product_tmpl_id.bhz_seller_id", store=True, readonly=True)
    active = fields.Boolean(default=True)
    budget = fields.Float()
    spent = fields.Float()
    boost = fields.Float(help="Multiplicador de boost (1.0 padrão)")
