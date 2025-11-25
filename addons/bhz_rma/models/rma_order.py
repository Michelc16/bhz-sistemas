from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BhzRmaOrder(models.Model):
    _name = "bhz.rma.order"
    _description = "BHZ RMA - Produtos com Defeito"
    _order = "create_date desc"

    name = fields.Char(
        string="Número RMA",
        required=True,
        copy=False,
        default=lambda self: _("Novo"),
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
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
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        help="Cliente que devolveu o produto com defeito.",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Produto",
        required=True,
        domain=[("type", "in", ("product", "consu"))],
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidade",
        required=True,
        readonly=False,
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
        help="Localização de onde o produto será retirado para o estoque de RMA.",
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

    # Estados do fluxo de RMA
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

    # Movimentos de estoque
    move_in_id = fields.Many2one(
        "stock.move",
        string="Movimento para RMA",
        readonly=True,
        help="Movimentação de estoque do estoque normal para o estoque de RMA.",
    )

    move_out_id = fields.Many2one(
        "stock.move",
        string="Movimento de retorno",
        readonly=True,
        help="Movimentação de estoque do RMA de volta ao estoque normal.",
    )

    # Custos para análise de prejuízo
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

    note = fields.Text(
        string="Observações",
    )

    @api.depends("product_id", "quantity", "company_id")
    def _compute_costs(self):
        for rma in self:
            if rma.product_id:
                # padrão: custo = standard_price do produto na empresa
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
        return super(BhzRmaOrder, self).create(vals)

    # -----------------------
    # AÇÕES DO WORKFLOW
    # -----------------------

    def action_set_waiting(self):
        """Coloca o RMA em 'Em espera' e move o produto para o estoque de RMA."""
        for rma in self:
            if rma.state not in ("draft",):
                raise UserError(
                    _(
                        "Apenas RMAs em Rascunho podem ser colocados em 'Em espera'.\n"
                        "RMA %s está em estado: %s"
                    )
                    % (rma.name, rma.state)
                )
            rma._check_quantities()
            rma._create_move_to_rma()
            rma.state = "waiting"

    def action_set_with_supplier(self):
        """Marca o RMA como 'Com fornecedor' (produto continua em estoque RMA)."""
        for rma in self:
            if rma.state not in ("waiting", "no_warranty"):
                raise UserError(
                    _(
                        "Apenas RMAs em 'Em espera' ou 'Sem garantia' podem ser marcados como 'Com fornecedor'."
                    )
                )
            rma.state = "with_supplier"

    def action_set_no_warranty(self):
        """Marca o RMA como 'Sem garantia' (produto continua no estoque RMA)."""
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
        Marca o RMA como 'Solucionado' e devolve o produto do estoque RMA
        para o estoque normal.
        """
        for rma in self:
            if rma.state not in ("waiting", "with_supplier", "no_warranty"):
                raise UserError(
                    _(
                        "Apenas RMAs em 'Em espera', 'Com fornecedor' ou 'Sem garantia' "
                        "podem ser marcados como 'Solucionado'."
                    )
                )
            rma._create_move_from_rma()
            rma.state = "solved"

    def action_cancel(self):
        """Cancela o RMA. Não mexe no estoque se já foi movimentado."""
        for rma in self:
            if rma.state == "solved":
                raise UserError(
                    _("Não é possível cancelar um RMA já solucionado.")
                )
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
        """Cria o movimento de estoque do local de origem para o estoque de RMA."""
        for rma in self:
            rma._check_quantities()

            if rma.move_in_id:
                # Já existe movimento de entrada em RMA
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
            # Confirma e faz o movimento
            move._action_confirm()
            move._action_done()

            rma.move_in_id = move.id

    def _create_move_from_rma(self):
        """
        Cria o movimento de estoque do local de RMA de volta para
        o local de origem.
        """
        for rma in self:
            rma._check_quantities()

            if rma.move_out_id:
                # Já existe movimento de retorno
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
