# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class BhzIFoodOrder(models.Model):
    _name = "bhz.ifood.order"
    _description = "Pedido iFood"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(default="/", copy=False, readonly=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    account_id = fields.Many2one("bhz.ifood.account", required=True, ondelete="restrict")

    ifood_order_id = fields.Char(index=True, required=True, copy=False)
    status = fields.Char(tracking=True)

    customer_name = fields.Char()
    customer_phone = fields.Char()
    delivery_address = fields.Char()

    total_amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    raw_payload = fields.Text()

    sale_order_id = fields.Many2one("sale.order", copy=False, readonly=True)
    state = fields.Selection([
        ("new", "Novo"),
        ("imported", "Importado"),
        ("error", "Erro"),
    ], default="new", tracking=True)

    _sql_constraints = [
        ("uniq_ifood_order_company", "unique(ifood_order_id, company_id)", "Pedido iFood já importado para esta empresa."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = seq.next_by_code("bhz.ifood.order") or "/"
        return super().create(vals_list)

    def action_import_to_sale(self):
        """Cria sale.order a partir do payload cru. (Você melhora o parsing depois)"""
        for rec in self:
            if rec.sale_order_id:
                continue
            if not rec.raw_payload:
                raise UserError(_("Sem payload para importar."))

            data = json.loads(rec.raw_payload)

            partner = rec._get_or_create_partner(data)
            so_vals = {
                "company_id": rec.company_id.id,
                "partner_id": partner.id,
                "origin": f"iFood {rec.ifood_order_id}",
            }
            so = self.env["sale.order"].create(so_vals)

            # Linhas (MVP): você vai mapear itens reais depois
            # Recomendado: criar bhz.ifood.product.map e resolver product_id
            # Aqui criamos uma linha genérica.
            product = self.env.ref("sale.product_product_delivery", raise_if_not_found=False)
            if product:
                self.env["sale.order.line"].create({
                    "order_id": so.id,
                    "product_id": product.id,
                    "name": f"Pedido iFood {rec.ifood_order_id}",
                    "product_uom_qty": 1,
                    "price_unit": rec.total_amount or 0.0,
                })

            rec.sale_order_id = so.id
            rec.state = "imported"

    def _get_or_create_partner(self, data: dict):
        name = (data.get("customer") or {}).get("name") or self.customer_name or "Cliente iFood"
        phone = (data.get("customer") or {}).get("phone") or self.customer_phone
        Partner = self.env["res.partner"].with_company(self.company_id).sudo()
        domain = [("name", "=", name), ("company_id", "in", [self.company_id.id, False])]
        if phone:
            domain = ["|", ("phone", "=", phone), ("mobile", "=", phone)] + domain
        partner = Partner.search(domain, limit=1)
        if not partner:
            partner = Partner.create({
                "name": name,
                "phone": phone,
                "company_id": self.company_id.id,
            })
        return partner
