# -*- coding: utf-8 -*-
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
        string="Número RMA",
        readonly=True,
        default="Novo",
        tracking=True,
    )

    date_rma = fields.Date(
        string="Data do RMA",
        default=fields.Date.today,
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente / Fornecedor",
        tracking=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Produto",
        required=True,
        tracking=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidade de Medida",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit"),
    )

    quantity = fields.Float(
        string="Quantidade",
        default=1,
        required=True,
    )

    lot_id = fields.Many2one(
        "stock.lot",
        string="Número de Série / Lote",
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

    warranty_type = fields.Selection(
        [
            ("cliente", "Garantia do Cliente"),
            ("fornecedor", "Garantia do Fornecedor"),
            ("sem", "Sem Garantia"),
        ],
        string="Tipo de Garantia",
        default="fornecedor",
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("waiting", "Em espera"),
            ("with_supplier", "Com fornecedor"),
            ("no_warranty", "Sem garantia"),
            ("solved", "Solucionado"),
            ("cancelled", "Cancelado"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    location_id = fields.Many2one(
        "stock.location",
        string="Local de Origem",
        required=True,
    )

    rma_location_id = fields.Many2one(
        "stock.location",
        string="Local de RMA",
        required=True,
    )

    note = fields.Text(string="Observações")

    # === 🔥 CAMPO QUE FALTAVA E ESTAVA QUEBRANDO O XML ===
    service_order_id = fields.Many2one(
        "bhz.rma.service.order",
        string="Ordem de Serviço",
    )

    # =========================================================
    # CÁLCULOS AUTOMÁTICOS
    # =========================================================
    @api.depends("product_id")
    def _compute_unit_cost(self):
        for rec in self:
            rec.unit_cost = rec.product_id.standard_price or 0.0

            # Ajusta UoM baseada no produto
            if rec.product_id:
                rec.product_uom_id = rec.product_id.uom_id

    @api.depends("unit_cost", "quantity")
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.unit_cost * rec.quantity

    # =========================================================
    # CREATE MULTI — compatível com Odoo 18 / 19
    # =========================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") in ["Novo", _("Novo")]:
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("bhz.rma.order")
                    or _("Novo")
                )
        return super().create(vals_list)

    # =========================================================
    # BOTÕES DE STATUS (DEVEM CORRESPONDER AO FORM)
    # =========================================================
    def action_set_waiting(self):
        self.write({"state": "waiting"})

    def action_set_with_supplier(self):
        self.write({"state": "with_supplier"})

    def action_set_no_warranty(self):
        self.write({"state": "no_warranty"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_solved(self):
        for rec in self:
            if rec.warranty_type == "fornecedor":
                rec.action_return_from_rma()
        self.write({"state": "solved"})

    # =========================================================
    # MOVIMENTAÇÃO DE ESTOQUE
    # =========================================================
    def action_move_to_rma_stock(self):
        for rec in self:
            if not rec.location_id or not rec.rma_location_id:
                raise UserError("Defina os locais de origem e RMA.")

            self.env["stock.move"].create(
                {
                    "name": f"RMA {rec.name}",
                    "product_id": rec.product_id.id,
                    "product_uom": rec.product_uom_id.id,
                    "product_uom_qty": rec.quantity,
                    "location_id": rec.location_id.id,
                    "location_dest_id": rec.rma_location_id.id,
                    "lot_id": rec.lot_id.id if rec.lot_id else False,
                }
            )._action_confirm()._action_done()

    def action_return_from_rma(self):
        for rec in self:
            self.env["stock.move"].create(
                {
                    "name": f"Retorno RMA {rec.name}",
                    "product_id": rec.product_id.id,
                    "product_uom": rec.product_uom_id.id,
                    "product_uom_qty": rec.quantity,
                    "location_id": rec.rma_location_id.id,
                    "location_dest_id": rec.location_id.id,
                    "lot_id": rec.lot_id.id if rec.lot_id else False,
                }
            )._action_confirm()._action_done()

    # =========================================================
    # RELATÓRIO & E-MAIL
    # =========================================================
    def action_print_rma(self):
        return self.env.ref("bhz_rma.action_report_bhz_rma_order").report_action(self)

    def action_send_rma_email(self):
        template = self.env.ref("bhz_rma.email_template_bhz_rma_order", raise_if_not_found=False)
        if not template:
            raise UserError("Template de e-mail não encontrado.")
        return template.send_mail(self.id, force_send=True)
