# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def bhz_ai_create_order(self, partner_id, order_lines):
        """
        Params:
          partner_id: int
          order_lines: [{product_id:int, qty:float, price_unit:float(optional)}]
        """
        if not partner_id:
            raise UserError("partner_id obrigatório.")
        if not order_lines:
            raise UserError("order_lines obrigatório.")

        partner = self.env["res.partner"].browse(int(partner_id)).exists()
        if not partner:
            raise UserError("Cliente não encontrado.")

        lines_vals = []
        for l in order_lines:
            product = self.env["product.product"].browse(int(l.get("product_id"))).exists()
            if not product:
                raise UserError("Produto inválido.")
            qty = float(l.get("qty") or 0.0)
            if qty <= 0:
                raise UserError("qty precisa ser > 0.")
            vals = {
                "product_id": product.id,
                "product_uom_qty": qty,
            }
            if l.get("price_unit") is not None:
                vals["price_unit"] = float(l["price_unit"])
            lines_vals.append((0, 0, vals))

        so = self.create({
            "partner_id": partner.id,
            "order_line": lines_vals,
        })
        return {"sale_order_id": so.id, "name": so.name}
