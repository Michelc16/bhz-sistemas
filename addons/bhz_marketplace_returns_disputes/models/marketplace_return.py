# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzMarketplaceReturn(models.Model):
    _name = "bhz.marketplace.return"
    _description = "Devolução/Disputa de Marketplace"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    sale_order_id = fields.Many2one("sale.order", required=True, ondelete="cascade")
    sale_order_line_id = fields.Many2one("sale.order.line", required=True, ondelete="cascade")
    seller_id = fields.Many2one(related="sale_order_line_id.bhz_seller_id", store=True, readonly=True)
    reason = fields.Selection([
        ("not_received", "Não recebi"),
        ("defective", "Defeituoso"),
        ("regret", "Desistência"),
        ("wrong_item", "Item errado"),
    ], required=True, tracking=True)
    description = fields.Text(tracking=True)
    evidence = fields.Binary("Evidência")
    evidence_filename = fields.Char()
    state = fields.Selection([
        ("opened", "Aberta"),
        ("seller_response", "Aguardando vendedor"),
        ("mediation", "Mediação"),
        ("approved_refund", "Reembolso aprovado"),
        ("rejected", "Rejeitada"),
        ("closed", "Fechada"),
    ], default="opened", tracking=True)
    refund_amount = fields.Monetary()
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)

    def action_approve_refund(self):
        Move = self.env["bhz.seller.ledger.move"]
        for rec in self:
            Move.create({
                "seller_id": rec.seller_id.id,
                "date": fields.Date.context_today(self),
                "move_type": "refund_debit",
                "amount": -rec.refund_amount,
                "sale_order_id": rec.sale_order_id.id,
                "sale_order_line_id": rec.sale_order_line_id.id,
                "ref": rec.sale_order_id.name,
                "note": "Reembolso aprovado",
            })
            rec.state = "approved_refund"

    def action_set_state(self, new_state):
        self.write({"state": new_state})
