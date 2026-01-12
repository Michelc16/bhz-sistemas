# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_seller_shipments(self):
        Shipment = self.env["bhz.seller.shipment"]
        for order in self:
            seller_map = {}
            for line in order.order_line:
                if not line.bhz_seller_id:
                    continue
                seller_map.setdefault(line.bhz_seller_id.id, []).append(line)
            for seller_id, lines in seller_map.items():
                shipment = Shipment.create({
                    "sale_order_id": order.id,
                    "seller_id": seller_id,
                    "state": "ready",
                })
                for l in lines:
                    self.env["bhz.seller.shipment.line"].create({
                        "shipment_id": shipment.id,
                        "sale_order_line_id": l.id,
                    })

    def action_confirm(self):
        res = super().action_confirm()
        self._create_seller_shipments()
        return res
