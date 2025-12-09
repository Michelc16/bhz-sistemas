from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bhz_margin_percent = fields.Float(
        string="Margem de lucro (%)",
        help="Margem fixa usada para calcular automaticamente o preço de venda "
             "com base no custo.",
        default=0.0,
    )

    bhz_qty_physical = fields.Float(
        string="Estoque físico",
        compute="_compute_bhz_stock_quantities",
        digits="Product Unit of Measure",
        help="Quantidade física em estoque (on hand).",
    )
    bhz_qty_reserved = fields.Float(
        string="Estoque reservado",
        compute="_compute_bhz_stock_quantities",
        digits="Product Unit of Measure",
        help="Quantidade do físico que já está reservada em pedidos.",
    )
    bhz_qty_available = fields.Float(
        string="Estoque disponível",
        compute="_compute_bhz_stock_quantities",
        digits="Product Unit of Measure",
        help="Estoque físico menos estoque reservado.",
    )

    @api.depends("qty_available", "free_qty")
    def _compute_bhz_stock_quantities(self):
        for product in self:
            physical = product.qty_available
            free = product.free_qty
            reserved = max(physical - free, 0.0)
            product.bhz_qty_physical = physical
            product.bhz_qty_reserved = reserved
            product.bhz_qty_available = free

    @api.onchange("bhz_margin_percent", "standard_price")
    def _onchange_bhz_margin_or_cost(self):
        """Sempre que custo ou margem mudar no produto,
        recalcula automaticamente o preço de venda.
        """
        for product in self:
            if product.standard_price and product.bhz_margin_percent:
                product.list_price = product.standard_price * (
                    1.0 + (product.bhz_margin_percent / 100.0)
                )
