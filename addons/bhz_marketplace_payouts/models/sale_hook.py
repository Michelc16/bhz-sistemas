# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _log_sale_to_ledger(self, orders):
        Move = self.env["bhz.seller.ledger.move"]
        Rule = self.env["bhz.marketplace.commission.rule"]
        for order in orders:
            for line in order.order_line:
                seller = line.bhz_seller_id
                if not seller:
                    continue
                # crédito de venda
                Move.create({
                    "seller_id": seller.id,
                    "date": order.date_order.date(),
                    "move_type": "sale_credit",
                    "amount": line.price_subtotal,
                    "sale_order_id": order.id,
                    "sale_order_line_id": line.id,
                    "ref": order.name,
                    "note": "Crédito de venda",
                })
                # comissão
                rate = seller.commission_rate or 0.0
                rule = Rule.match_rule(seller.id, line.product_id.categ_id.id)
                if rule:
                    rate = rule.commission_rate
                if rate:
                    Move.create({
                        "seller_id": seller.id,
                        "date": order.date_order.date(),
                        "move_type": "commission_debit",
                        "amount": - (line.price_subtotal * rate / 100.0),
                        "sale_order_id": order.id,
                        "sale_order_line_id": line.id,
                        "ref": order.name,
                        "note": f"Comissão {rate}%",
                    })

    def action_confirm(self):
        res = super().action_confirm()
        self._log_sale_to_ledger(self)
        # shipping handled in shipping module (if installed)
        return res
