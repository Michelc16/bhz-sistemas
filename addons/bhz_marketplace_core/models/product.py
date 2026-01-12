# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bhz_seller_id = fields.Many2one("bhz.marketplace.seller", string="Seller", index=True)
    bhz_marketplace_state = fields.Selection([
        ("draft", "Rascunho"),
        ("pending", "Pendente"),
        ("approved", "Aprovado"),
        ("rejected", "Rejeitado"),
        ("archived", "Arquivado"),
    ], default="draft", tracking=True)

    def action_send_to_review(self):
        self.write({"bhz_marketplace_state": "pending"})

    def action_approve_marketplace(self):
        self.write({"bhz_marketplace_state": "approved", "website_published": True})

    def action_reject_marketplace(self):
        self.write({"bhz_marketplace_state": "rejected"})


class ProductProduct(models.Model):
    _inherit = "product.product"

    bhz_seller_id = fields.Many2one(related="product_tmpl_id.bhz_seller_id", store=True, readonly=True)
