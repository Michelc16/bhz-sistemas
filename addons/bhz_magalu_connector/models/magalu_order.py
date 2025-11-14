import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BhzMagaluOrder(models.Model):
    _name = "bhz.magalu.order"
    _description = "Pedidos Magalu"
    _check_company_auto = True

    name = fields.Char("Pedido Magalu", required=True)
    config_id = fields.Many2one("bhz.magalu.config", required=True)
    company_id = fields.Many2one(related="config_id.company_id", store=True, readonly=True)
    sale_id = fields.Many2one("sale.order", string="Pedido de Venda Odoo")
    raw_json = fields.Text("JSON original")

    @api.model
    def cron_fetch_orders(self):
        configs = self.env["bhz.magalu.config"].search([])
        for cfg in configs:
            self._fetch_for_config(cfg)

    def _fetch_for_config(self, config):
        api = self.env["bhz.magalu.api"]
        data = api.fetch_orders(config)
        orders = data.get("orders") or data.get("items") or []
        for o in orders:
            order_id = o.get("id") or o.get("code")
            if not order_id:
                continue
            if self.search([("name", "=", order_id), ("config_id", "=", config.id)]):
                continue
            partner = self._get_or_create_partner(o, config.company_id.id)
            sale = self._create_sale(order_id, partner, o, config.company_id.id)
            self.create({
                "name": order_id,
                "config_id": config.id,
                "sale_id": sale.id,
                "raw_json": json.dumps(o, ensure_ascii=False),
            })

    def _get_or_create_partner(self, order_data, company_id):
        customer = order_data.get("customer", {})
        email = customer.get("email")
        partner = self.env["res.partner"].search([("email", "=", email)], limit=1)
        if not partner:
            partner = self.env["res.partner"].create({
                "name": customer.get("name") or "Cliente Magalu",
                "email": email,
                "phone": customer.get("phone"),
                "company_id": company_id,
            })
        return partner

    def _create_sale(self, order_id, partner, order_data, company_id):
        order_lines = []
        for item in order_data.get("items", []):
            sku = item.get("sku")
            product = self.env["product.product"].search([("default_code", "=", sku)], limit=1)
            if not product:
                product = self.env["product.product"].create({
                    "name": item.get("name") or sku,
                    "default_code": sku,
                    "lst_price": item.get("price", 0.0),
                    "company_id": company_id,
                })
            order_lines.append((0, 0, {
                "product_id": product.id,
                "name": product.name,
                "product_uom_qty": item.get("quantity", 1.0),
                "price_unit": item.get("price", 0.0),
            }))
        sale = self.env["sale.order"].create({
            "partner_id": partner.id,
            "origin": f"Magalu {order_id}",
            "order_line": order_lines,
            "company_id": company_id,
        })
        sale.action_confirm()
        return sale
