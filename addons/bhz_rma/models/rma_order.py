from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BhzRmaOrder(models.Model):
    _name = "bhz.rma.order"
    _description = "BHZ RMA - Produtos com Defeito"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Número RMA",
        required=True,
        copy=False,
        default=lambda self: _("Novo"),
        readonly=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    date_rma = fields.Datetime(
        string="Data do RMA",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        help="Cliente que devolveu o produto com defeito.",
        tracking=True,
    )

    warranty_type = fields.Selection(
        [
            ("supplier", "Garantia do fornecedor"),
            ("customer", "Garantia do cliente"),
            ("none", "Sem garantia"),
        ],
        string="Tipo de garantia",
        default="supplier",
        required=True,
        tracking=True,
        help=(
            "Garantia do fornecedor: produto sai do estoque e entra no estoque RMA, "
            "podendo voltar ao estoque normal.\n"
            "Garantia do cliente: gera uma Ordem de Serviço, permite troca de peça "
            "para o cliente, colocando peça com defeito no estoque RMA e tirando peça nova do estoque."
        ),
    )

    product_id = fields.Many2one(
        "product.product",
        string="Produto",
        required=True,
        domain=[("type", "in", ("product", "consu"))],
        tracking=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidade",
        required=True,
    )

    quantity = fields.Float(
        string="Quantidade",
        default=1.0,
        required=True,
    )

    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote/Série",
        domain="[('product_id', '=', product_id)]",
        help="Lote ou número de série do produto, se aplicável.",
    )

    location_id = fields.Many2one(
        "stock.location",
        string="Local de Origem",
        required=True,
        domain=[("usage", "=", "internal")],
        default=lambda self: self.env.ref(
            "stock.stock_location_stock", raise_if_not_found=False
        ),
        help="Localização de onde o produto será retirado ou usado no processo.",
    )

    rma_location_id = fields.Many2one(
        "stock.location",
        string="Local de RMA",
        required=True,
        domain=[("usage", "=", "internal")],
        default=lambda self: self.env.ref(
            "bhz_rma.stock_location_rma", raise_if_not_found=False
        ),
        help="Localização de estoque específica para produtos em RMA.",
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
        required=True,
        tracking=True,
    )

    move_in_id = fields.Many2one(
        "stock.move",
        string="Movimento para RMA / peça defeituosa",
        readonly=True,
        help="Movimentação de estoque para o estoque de RMA (peça defeituosa).",
    )

    move_out_id = fields.Many2one(
        "stock.move",
        string="Movimento de retorno / peça nova",
        readonly=True,
        help="Movimentação de estoque para saída de produto ou peça nova.",
    )

    unit_cost = fields.Monetary(
        string="Custo unitário",
        currency_field="currency_id",
        compute="_compute_costs",
        store=True,
    )

    total_cost = fields.Monetary(
        string="Custo total (prejuízo potencial)",
        currency_field="currency_id",
        compute="_compute_costs",
        store=True,
    )

    note = fields.Text(string="Observações")

    service_order_id = fields.Many2one(
        "bhz.rma.service.order",
        string="Ordem de Serviço",
        readonly=True,
    )

    @api.depends("product_id", "quantity", "company_id")
    def _compute_costs(self):
        for rma in self:
            if rma.product_id:
                rma.unit_cost = rma.product_id.standard_price or 0.0
            else:
                rma.unit_cost = 0.0
            rma.total_cost = (rma.unit_cost or 0.0) * (rma.quantity or 0.0)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rma in self:
            if rma.product_id:
                rma.product_uom_id = rma.product_id.uom_id

    @api.model
    def create(self, vals):
        if not vals.get("name") or vals.get("name") == _("Novo"):
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("bhz.rma.order") or _("Novo")
            )
        return super().create(vals)

    # -----------------------
    # AÇÕES DO WORKFLOW
    # -----------------------

    def action_set_waiting(self):
        """
        Coloca o RMA em 'Em espera'.

        - Garantia do fornecedor:
          move o produto do local de origem para o estoque RMA.
        - Garantia do cliente:
          cria uma Ordem de Serviço ligada ao RMA (sem mexer no estoque ainda).
        """
        for rma in self:
            if rma.state != "draft":
                raise UserError(
                    _(
                        "Apenas RMAs em Rascunho podem ser colocados em 'Em espera'.\n"
                        "RMA %s está em estado: %s"
                    )
                    % (rma.name, rma.state)
                )

            rma._check_quantities()

            if rma.warranty_type == "supplier":
                rma._create_move_to_rma()
            elif rma.warranty_type == "customer":
                rma._ensure_service_order()

            rma.state = "waiting"

    def action_set_with_supplier(self):
        for rma in self:
            if rma.state not in ("waiting", "no_warranty"):
                raise UserError(
                    _(
                        "Apenas RMAs em 'Em espera' ou 'Sem garantia' podem ser marcados como 'Com fornecedor'."
                    )
                )
            rma.state = "with_supplier"

    def action_set_no_warranty(self):
        for rma in self:
            if rma.state not in ("waiting", "with_supplier"):
                raise UserError(
                    _(
                        "Apenas RMAs em 'Em espera' ou 'Com fornecedor' podem ser marcados como 'Sem garantia'."
                    )
                )
            rma.state = "no_warranty"

    def action_solved(self):
        """
        Marca o RMA como 'Solucionado'.

        - Garantia do fornecedor:
          devolve produto do RMA para o estoque normal.
        - Garantia do cliente:
          não devolve nada ao estoque; a lógica de troca é feita na Ordem de Serviço.
        """
        for rma in self:
            if rma.state not in ("waiting", "with_supplier", "no_warranty"):
                raise UserError(
                    _(
                        "Apenas RMAs em 'Em espera', 'Com fornecedor' ou 'Sem garantia' "
                        "podem ser marcados como 'Solucionado'."
                    )
                )

            if rma.warranty_type == "supplier":
                rma._create_move_from_rma()

            if rma.service_order_id and rma.service_order_id.state != "done":
                rma.service_order_id.state = "done"

            rma.state = "solved"

    def action_cancel(self):
        for rma in self:
            if rma.state == "solved":
                raise UserError(_("Não é possível cancelar um RMA já solucionado."))
            rma.state = "cancelled"

    # -----------------------
    # MOVIMENTAÇÕES DE ESTOQUE
    # -----------------------

    def _check_quantities(self):
        for rma in self:
            if rma.quantity <= 0:
                raise UserError(_("A quantidade deve ser maior que zero."))

            if not rma.product_uom_id:
                raise UserError(
                    _("Defina a unidade de medida para o produto do RMA.")
                )

            if not rma.location_id or not rma.rma_location_id:
                raise UserError(
                    _("Defina o local de origem e o local de RMA antes de continuar.")
                )

    def _create_move_to_rma(self):
        """Garantia do fornecedor: move produto do local de origem para o estoque RMA."""
        for rma in self:
            rma._check_quantities()

            if rma.move_in_id:
                continue

            Move = self.env["stock.move"]

            move_vals = {
                "name": "%s - para RMA" % (rma.name,),
                "company_id": rma.company_id.id,
                "product_id": rma.product_id.id,
                "product_uom": rma.product_uom_id.id,
                "product_uom_qty": rma.quantity,
                "location_id": rma.location_id.id,
                "location_dest_id": rma.rma_location_id.id,
                "origin": rma.name,
            }

            if rma.lot_id:
                move_vals["restrict_lot_id"] = rma.lot_id.id

            move = Move.create(move_vals)
            move._action_confirm()
            move._action_done()

            rma.move_in_id = move.id

    def _create_move_from_rma(self):
        """Garantia do fornecedor: move produto do estoque RMA de volta ao estoque normal."""
        for rma in self:
            rma._check_quantities()

            if rma.move_out_id:
                continue

            Move = self.env["stock.move"]

            move_vals = {
                "name": "%s - retorno de RMA" % (rma.name,),
                "company_id": rma.company_id.id,
                "product_id": rma.product_id.id,
                "product_uom": rma.product_uom_id.id,
                "product_uom_qty": rma.quantity,
                "location_id": rma.rma_location_id.id,
                "location_dest_id": rma.location_id.id,
                "origin": rma.name,
            }

            if rma.lot_id:
                move_vals["restrict_lot_id"] = rma.lot_id.id

            move = Move.create(move_vals)
            move._action_confirm()
            move._action_done()

            rma.move_out_id = move.id

    # -----------------------
    # ORDEM DE SERVIÇO (GARANTIA CLIENTE)
    # -----------------------

    def _ensure_service_order(self):
        """Cria Ordem de Serviço vinculada ao RMA, se ainda não existir."""
        ServiceOrder = self.env["bhz.rma.service.order"]
        for rma in self:
            if rma.service_order_id:
                continue

            vals = {
                "rma_id": rma.id,
                "partner_id": rma.partner_id.id,
                "product_id": rma.product_id.id,
                "quantity": rma.quantity,
                "company_id": rma.company_id.id,
            }
            so = ServiceOrder.create(vals)
            rma.service_order_id = so.id

    # -----------------------
    # IMPRESSÃO E E-MAIL
    # -----------------------

    def action_print_rma(self):
        """Imprime o pedido de RMA (PDF)."""
        self.ensure_one()
        return self.env.ref("bhz_rma.action_report_bhz_rma_order").report_action(self)

    def action_send_rma_email(self):
        """Envia o pedido de RMA por e-mail usando template."""
        self.ensure_one()
        template = self.env.ref(
            "bhz_rma.email_template_bhz_rma_order", raise_if_not_found=False
        )
        if not template:
            raise UserError(_("Template de e-mail do RMA não foi configurado."))
        if not self.partner_id or not self.partner_id.email:
            raise UserError(
                _("Defina um cliente com e-mail para enviar o pedido de RMA.")
            )
        template.send_mail(self.id, force_send=True)
        return True
