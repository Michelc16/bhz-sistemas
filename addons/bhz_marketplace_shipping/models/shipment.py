# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzSellerShipment(models.Model):
    _name = "bhz.seller.shipment"
    _description = "Envio por seller"
    _order = "create_date desc"

    sale_order_id = fields.Many2one("sale.order", required=True, ondelete="cascade")
    seller_id = fields.Many2one("bhz.marketplace.seller", required=True, index=True)
    state = fields.Selection([
        ("draft", "Rascunho"),
        ("ready", "Pronto"),
        ("shipped", "Enviado"),
        ("delivered", "Entregue"),
        ("cancel", "Cancelado"),
    ], default="draft")
    tracking_code = fields.Char()
    carrier_id = fields.Many2one("delivery.carrier", string="Transportadora")
    note = fields.Text()
    line_ids = fields.One2many("bhz.seller.shipment.line", "shipment_id", string="Linhas")

    def action_ready(self):
        self.write({"state": "ready"})

    def action_shipped(self):
        self.write({"state": "shipped"})

    def action_delivered(self):
        self.write({"state": "delivered"})

    def action_cancel(self):
        self.write({"state": "cancel"})


class BhzSellerShipmentLine(models.Model):
    _name = "bhz.seller.shipment.line"
    _description = "Linha de envio"

    shipment_id = fields.Many2one("bhz.seller.shipment", required=True, ondelete="cascade")
    sale_order_line_id = fields.Many2one("sale.order.line", required=True, ondelete="cascade")
    product_id = fields.Many2one(related="sale_order_line_id.product_id", store=True)
    qty = fields.Float(related="sale_order_line_id.product_uom_qty", store=True)
