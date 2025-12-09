from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BhzRmaOrder(models.Model):
    _name = "bhz.rma.order"
    _description = "BHZ RMA - Controle de Produtos com Defeito"
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
            ("sem_garantia", "Sem Garantia"),
            ("solved", "Solucionado"),
            ("cancelled", "Cancelado"),
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
        default=lambda self: self.env.ref(
            "stock.stock_location_stock", raise_if_not_found=False
        ),
    )

    rma_location_id = fields.Many2one(
        "stock.location",
        string="Local de RMA",
        required=True,
        default=lambda self: self.env.ref(
            "bhz_rma.stock_location_rma", raise_if_not_found=False
        ),
    )

    unit_cost = fields.Float(
        string="Custo Unitário",
        compute="_compute_unit_cost",
        store=True,
    )

    total_cost = fields.Float(
        string="Custo Total",
        compute="_compute_total_cost",
        store=True,
    )

    # =========================================================
    # COMPUTES
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
    # CREATE — SUPORTA LISTA E DICT
    # =========================================================

    @api.model
    def create(self, vals):
        # Normaliza para lista
        if isinstance(vals, list):
            vals_list = vals
        else:
            vals_list = [vals]

        seq = self.env["ir.sequence"]

        for v in vals_list:
            if not v.get("name") or v.get("name") in ("Novo", _("Novo")):
                v["name"] = seq.next_by_code("bhz.rma.order") or "Novo"

        if len(vals_list) == 1:
            return super().create(vals_list[0])
        else:
            return super().create(vals_list)

    # =========================================================
    # AÇÕES DE ESTOQUE
    # =========================================================

    def action_move_to_rma_stock(self):
        """Move do estoque normal para o estoque RMA."""
        for rec in self:
            if rec.quantity <= 0:
                raise UserError("A quantidade deve ser maior que zero.")

            move = self.env["stock.move"].create(
                {
                    "name": f"Entrada RMA {rec.name}",
                    "product_id": rec.product_id.id,
                    "product_uom": rec.product_id.uom_id.id,
                    "product_uom_qty": rec.quantity,
                    "location_id": rec.location_id.id,
                    "location_dest_id": rec.rma_location_id.id,
                }
            )
            move._action_confirm()
            move._action_done()

            rec.state = "waiting"

    def action_return_from_rma(self):
        """Retorna o produto ao estoque normal."""
        for rec in self:
            move = self.env["stock.move"].create(
                {
                    "name": f"Retorno RMA {rec.name}",
                    "product_id": rec.product_id.id,
                    "product_uom": rec.product_id.uom_id.id,
                    "product_uom_qty": rec.quantity,
                    "location_id": rec.rma_location_id.id,
                    "location_dest_id": rec.location_id.id,
                }
            )
            move._action_confirm()
            move._action_done()

            rec.state = "solved"

    # =========================================================
    # BOTÕES DA VIEW (OBRIGATÓRIOS)
    # =========================================================

    def action_set_waiting(self):
        self.write({"state": "waiting"})

    def action_set_with_supplier(self):
        self.write({"state": "supplier"})

    def action_set_no_warranty(self):
        self.write({"state": "sem_garantia"})

    def action_solved(self):
        for rec in self:
            if rec.warranty_type == "fornecedor":
                rec.action_return_from_rma()
            else:
                rec.state = "solved"

    def action_cancel(self):
        """Cancela o RMA."""
        for rec in self:
            rec.state = "cancelled"

    # =========================================================
    # IMPRESSÃO DO RMA
    # =========================================================

    def action_print_rma(self):
        """Gera o PDF do RMA."""
        return self.env.ref("bhz_rma.action_report_bhz_rma_order").report_action(self)

    # =========================================================
    # ENVIO DE E-MAIL
    # =========================================================

    def action_send_rma_email(self):
        """Abre o popup de e-mail usando o template configurado."""
        self.ensure_one()

        template = self.env.ref(
            "bhz_rma.email_template_bhz_rma_order", raise_if_not_found=False
        )

        if not template:
            raise UserError("O template de e-mail de RMA não foi encontrado.")

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
