# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzSellerPayout(models.Model):
    _name = "bhz.seller.payout"
    _description = "Repasse ao seller"
    _order = "date_to desc, id desc"

    seller_id = fields.Many2one("bhz.marketplace.seller", required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    state = fields.Selection([
        ("draft", "Rascunho"),
        ("ready", "Pronto"),
        ("paid", "Pago"),
        ("cancel", "Cancelado"),
    ], default="draft")
    amount = fields.Monetary(compute="_compute_amount", store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)
    move_ids = fields.One2many("bhz.seller.ledger.move", "seller_id", string="Movimentos relacionados", compute="_compute_moves", store=False)

    @api.depends("seller_id", "date_from", "date_to")
    def _compute_amount(self):
        Move = self.env["bhz.seller.ledger.move"]
        for rec in self:
            domain = [
                ("seller_id", "=", rec.seller_id.id),
                ("date", ">=", rec.date_from),
                ("date", "<=", rec.date_to),
            ]
            total = sum(Move.search(domain).mapped("amount"))
            rec.amount = total

    @api.depends("seller_id")
    def _compute_moves(self):
        # helper to show moves; not stored
        return

    def action_set_ready(self):
        self.write({"state": "ready"})

    def action_mark_paid(self):
        Move = self.env["bhz.seller.ledger.move"]
        for rec in self:
            Move.create({
                "seller_id": rec.seller_id.id,
                "date": rec.date_to,
                "move_type": "payout_debit",
                "amount": -rec.amount,
                "ref": f"Payout {rec.id}",
                "note": "Repasse realizado",
            })
            rec.state = "paid"
