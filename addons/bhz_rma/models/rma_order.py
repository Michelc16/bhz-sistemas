from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BhzRmaOrder(models.Model):
    _name = "bhz.rma.order"
    _description = "BHZ RMA - Produtos com Defeito"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    # =========================================================
    # CAMPOS PRINCIPAIS
    # =========================================================

    name = fields.Char(
        string="Número do RMA",
        default="Novo",
        readonly=True,
        copy=False,
        tracking=True,
    )

    date_rma = fields.Date(
        string="Data do RMA",
        default=fields.Date.context_today,
        tracking=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        tracking=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Produto",
        required=True,
        tracking=True,
    )

    quantity = fields.Float(
        string="Quantidade",
        default=1.0,
        tracking=True,
    )

    warranty_type = fields.Selection(
        [
            ("cliente", "Garantia do Cliente"),
            ("fornecedor", "Garantia com Fornecedor"),
            ("sem_garantia", "Sem Garantia"),
        ],
        string="Tipo de Garantia",
        required=True,
        default="cliente",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("waiting", "Em Espera"),
            ("supplier", "Com Fornecedor"),
            ("solved", "Solucionado"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    note = fields.Text(string="Observações")

    # Estoques
    location_id = fields.Many2one(
        "stock.location",
        string="Local de Origem",
        required=True,
        default=lambda self: self.env.ref("stock.stock_location_stock", raise_if_not_found=False),
    )

    rma_location_id = fields.Many2one(
        "stock.location",
        string="Local de RMA",
        required=True,
        default=lambda self: self.env.ref("bhz_rma.stock_location_rma", raise_if_not_found=False),
    )

    unit_cost = fields.Float(
        string="Custo Unitário",
        compute="_compute_unit_cost",
        store=True,
    )

    total_cost = fields.Float(
        string="Custo Total (Prejuízo)",
        compute="_compute_total_cost",
        store=True,
    )

    # =========================================================
    # CÁLCULOS
    # =========================================================

    @api.depends("product_id")
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.product_id.standard_price or 0.0

    @api.depends("unit_cost", "quantity")
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.unit_cost * rec.quantity

    # =========================================================
    # MÉTODO CREATE (CORRIGIDO PARA ODOO 18/19)
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Corrige erro 'list' object has no attribute get' e gera sequência."""
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "Novo":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("bhz.rma.order")
                    or "Novo"
                )
        return super().create(vals_list)

    # =========================================================
    # AÇÕES DE ESTOQUE
    # =========================================================

    def action_move_to_rma_stock(self):
        """Baixa do estoque normal e move para local de RMA."""
        for rec in self:
            if rec.quantity <= 0:
                raise UserError("A quantidade deve ser maior que zero.")

            self.env["stock.move"].create(
                {
                    "name": f"Entrada RMA {rec.name}",
                    "product_id": rec.product_id.id,
                    "product_uom": rec.product_id.uom_id.id,
                    "product_uom_qty": rec.quantity,
                    "location_id": rec.location_id.id,
                    "location_dest_id": rec.rma_location_id.id,
                }
            )._action_confirm()._action_done()

            rec.state = "waiting"

    def action_return_from_rma(self):
        """Quando solucionado, volta o item ao estoque normal."""
        for rec in self:
            self.env["stock.move"].create(
                {
                    "name": f"Retorno RMA {rec.name}",
                    "product_id": rec.product_id.id,
                    "product_uom": rec.product_id.uom_id.id,
                    "product_uom_qty": rec.quantity,
                    "location_id": rec.rma_location_id.id,
                    "location_dest_id": rec.location_id.id,
                }
            )._action_confirm()._action_done()

            rec.state = "solved"

    # =========================================================
    # E-MAIL (ENVIO DO RMA)
    # =========================================================

    def action_send_rma_email(self):
        """Abre o popup para enviar o e-mail RMA."""
        template = self.env.ref("bhz_rma.email_template_bhz_rma_order", raise_if_not_found=False)

        if not template:
            raise UserError("Template de e-mail do RMA não encontrado.")

        return {
            "name": _("Enviar Pedido de RMA"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": "bhz.rma.order",
                "default_res_id": self.id,
                "default_use_template": True,
                "default_template_id": template.id,
                "force_email": True,
            },
        }
