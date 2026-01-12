# -*- coding: utf-8 -*-
from odoo import fields, models


class BhzSellerLedgerMove(models.Model):
    _name = "bhz.seller.ledger.move"
    _description = "Extrato do Seller"
    _order = "date desc, id desc"

    seller_id = fields.Many2one("bhz.marketplace.seller", required=True, index=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    ref = fields.Char()
    move_type = fields.Selection([
        ("sale_credit", "Crédito de venda"),
        ("commission_debit", "Débito de comissão"),
        ("shipping_debit", "Débito de frete"),
        ("refund_debit", "Débito de reembolso"),
        ("payout_debit", "Débito de repasse"),
        ("manual", "Manual"),
    ], required=True)
    amount = fields.Monetary("Valor", required=True, help="Crédito positivo, débito negativo.")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)
    sale_order_id = fields.Many2one("sale.order", ondelete="set null")
    sale_order_line_id = fields.Many2one("sale.order.line", ondelete="set null")
    note = fields.Text()
