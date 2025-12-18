from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bhz_margin_percent = fields.Float(
        string="Margem de lucro (%)",
        default=0.0,
        help="Margem fixa usada para calcular automaticamente o preço de venda.",
    )

    bhz_qty_physical = fields.Float(
        string="Estoque físico",
        compute="_compute_bhz_quantities",
        digits="Product Unit of Measure",
    )
    bhz_qty_reserved = fields.Float(
        string="Estoque reservado",
        compute="_compute_bhz_quantities",
        digits="Product Unit of Measure",
    )
    bhz_qty_available = fields.Float(
        string="Estoque disponível",
        compute="_compute_bhz_quantities",
        digits="Product Unit of Measure",
    )

    @api.depends("product_variant_ids.qty_available", "product_variant_ids.free_qty")
    def _compute_bhz_quantities(self):
        """Corrigido: cálculo baseado nas variáveis do product.product."""
        for template in self:
            physical = sum(template.product_variant_ids.mapped("qty_available"))
            free = sum(template.product_variant_ids.mapped("free_qty"))
            reserved = max(physical - free, 0)

            template.bhz_qty_physical = physical
            template.bhz_qty_reserved = reserved
            template.bhz_qty_available = free

    @api.onchange("bhz_margin_percent", "standard_price")
    def _onchange_margin_or_cost(self):
        """Recalcula preço automaticamente ao editar margem ou custo."""
        for product in self:
            if product.standard_price and product.bhz_margin_percent:
                product.list_price = product.standard_price * (
                    1 + (product.bhz_margin_percent / 100)
                )
