from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _bhz_update_product_cost_and_price(self):
        for line in self:
            product = line.product_id.product_tmpl_id
            if not product or not line.product_qty:
                continue

            # custo = preço unitário da linha de compra (sem impostos)
            new_cost = line.price_unit

            # atualiza custo padrão do produto
            product.standard_price = new_cost

            # se tiver margem cadastrada, recalcula preço de venda
            if product.bhz_margin_percent:
                product.list_price = new_cost * (
                    1.0 + (product.bhz_margin_percent / 100.0)
                )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        """Ao confirmar o pedido de compra:
        - Odoo já gera os movimentos de estoque (entrada).
        - Aqui só atualizamos custo e preço de venda.
        """
        res = super().button_confirm()

        for order in self:
            lines = order.order_line.filtered(
                lambda l: l.product_id and not l.display_type
            )
            lines._bhz_update_product_cost_and_price()

        return res
