# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzProductQuestion(models.Model):
    _name = "bhz.product.question"
    _description = "Pergunta de produto"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    product_tmpl_id = fields.Many2one("product.template", required=True, ondelete="cascade", index=True)
    seller_id = fields.Many2one(related="product_tmpl_id.bhz_seller_id", store=True, readonly=True)
    author_partner_id = fields.Many2one("res.partner", required=True, default=lambda self: self.env.user.partner_id)
    question = fields.Text(required=True, tracking=True)
    answer = fields.Text(tracking=True)
    state = fields.Selection([
        ("pending", "Pendente"),
        ("answered", "Respondida"),
        ("hidden", "Oculta"),
    ], default="pending", tracking=True)

    def action_answered(self):
        self.write({"state": "answered"})

    def action_hide(self):
        self.write({"state": "hidden"})

    @api.model
    def create_from_website(self, product_tmpl_id, question, partner=None):
        partner = partner or self.env.user.partner_id
        return self.create({
            "product_tmpl_id": product_tmpl_id,
            "question": question,
            "author_partner_id": partner.id,
        })
