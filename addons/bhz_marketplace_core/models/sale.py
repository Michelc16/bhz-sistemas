# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    bhz_seller_ids = fields.Many2many(
        "bhz.marketplace.seller", compute="_compute_sellers", string="Sellers", store=True, readonly=True)

    @api.depends("order_line.bhz_seller_id")
    def _compute_sellers(self):
        for order in self:
            sellers = order.order_line.mapped("bhz_seller_id")
            order.bhz_seller_ids = [(6, 0, sellers.ids)]


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bhz_seller_id = fields.Many2one(
        "bhz.marketplace.seller", compute="_compute_seller", store=True, readonly=True, index=True)

    @api.depends("product_id", "product_template_id")
    def _compute_seller(self):
        for line in self:
            seller = line.product_template_id.bhz_seller_id or line.product_id.bhz_seller_id
            line.bhz_seller_id = seller.id if seller else False
