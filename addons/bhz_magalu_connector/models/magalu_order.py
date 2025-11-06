from odoo import models, fields, api, _
from odoo.exceptions import UserError

class BhzMagaluOrder(models.Model):
    _name = "bhz.magalu.order"
    _description = "Pedidos Magalu"

    name = fields.Char("Pedido Magalu", required=True)
    config_id = fields.Many2one("bhz.magalu.config", required=True)
    sale_id = fields.Many2one("sale.order", string="Pedido de Venda Odoo")
    raw_json = fields.Text("JSON original")

    @api.model
    def cron_fetch_orders(self):
        configs = self.env["bhz.magalu.config"].search([])
        for cfg in configs:
            self.fetch_and_create_orders(cfg)

    def fetch_and_create_orders(self, config):
        api = self.env["bhz.magalu.api"]
        data = api.fetch_orders(config)
        orders = data.get("items") or data.get("orders") or []
        for o in orders:
            order_id = o.get("id") or o.get("code")
            if self.search([("name", "=", order_id), ("config_id", "=", config.id)]):
                continue
            partner = self._get_or_create_partner(o)
            sale = self._create_sale(order_id, partner, o)
            self.create({
                "name": order_id,
                "config_id": config.id,
                "sale_id": sale.id,
                "raw_json": o,
            })

    def _get_or_create_partner(self, order_data):
        customer = order_data.get("customer", {})
        name = customer.get("name") or "Cliente Magalu"
        email = customer.get("email")
        partner = self.env["res.partner"].search([("email", "=", email)], limit=1)
        if not partner:
            partner = self.env["res.partner"].create({
                "name": name,
                "email": email,
                "phone": customer.get("phone"),
                "street": customer.get("address", {}).get("street"),
            })
        return partner

    def _create_sale(self, order_id, partner, order_data):
        order_lines = []
        for item in order_data.get("items", []):
            sku = item.get("sku")
            product = self.env["product.product"].search([("default_code", "=", sku)], limit=1)
            if not product:
                product = self.env["product.product"].create({
                    "name": item.get("name") or sku,
                    "default_code": sku,
                    "lst_price": item.get("price", 0.0),
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
        })
        sale.action_confirm()
        return sale
