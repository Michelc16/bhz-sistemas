from odoo import models, fields, _
from odoo.exceptions import UserError

class BhzMagaluProduct(models.Model):
    _name = "bhz.magalu.product"
    _description = "Produtos Magalu"

    name = fields.Char(required=True)
    product_id = fields.Many2one("product.product", string="Produto Odoo", required=True)
    magalu_sku = fields.Char("SKU Magalu")
    config_id = fields.Many2one("bhz.magalu.config", string="Configuração", required=True)

    def action_push_to_magalu(self):
        api = self.env["bhz.magalu.api"]
        for rec in self:
            if not rec.product_id:
                raise UserError(_("Defina o produto Odoo."))
            product_vals = {
                "sku": rec.magalu_sku or rec.product_id.default_code,
                "name": rec.product_id.name,
                "description": rec.product_id.description_sale or rec.product_id.name,
                "price": rec.product_id.lst_price,
            }
            api.push_product(rec.config_id, product_vals)

    def action_sync_stock(self):
        api = self.env["bhz.magalu.api"]
        for rec in self:
            qty_available = rec.product_id.qty_available
            sku = rec.magalu_sku or rec.product_id.default_code
            api.push_stock(rec.config_id, sku, qty_available)
