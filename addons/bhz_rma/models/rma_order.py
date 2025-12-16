from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BhzRMAOrder(models.Model):
    _name = "bhz.rma.order"
    _description = "BHZ RMA"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="RMA",
        default="Novo",
        copy=False,
        readonly=True,
        tracking=True,
    )

    date_rma = fields.Date(
        string="Data do RMA",
        default=fields.Date.context_today,
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente / Fornecedor",
        tracking=True,
    )

    warranty_type = fields.Selection(
        [
            ("customer", "Garantia do Cliente (Loja)"),
            ("supplier", "Garantia do Fornecedor"),
            ("no_warranty", "Sem garantia"),
            ("production", "Defeito na produção (interno)"),
        ],
        string="Tipo de Garantia",
        default="supplier",
        tracking=True,
    )

    # ✅ Decide o que o botão "Solucionado" fará no estoque
    resolution_method = fields.Selection(
        [
            ("return_to_stock", "Voltar ao estoque padrão (RMA → Estoque)"),
            ("scrap_from_rma", "Retirar do estoque RMA (RMA → Sucata)"),
            ("none", "Não movimentar estoque"),
        ],
        string="Resolução (Solucionado)",
        default="return_to_stock",
        tracking=True,
        help=(
            "Define o comportamento do botão 'Solucionado'.\n"
            "- Voltar ao estoque: move do Local RMA para Local de origem.\n"
            "- Retirar do RMA: dá baixa do RMA para Sucata.\n"
            "- Não movimentar: apenas finaliza o RMA."
        ),
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

    product_id = fields.Many2one(
        "product.product",
        string="Produto",
        required=True,
        tracking=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidade de Medida",
        related="product_id.uom_id",
        store=True,
        readonly=True,
    )

    quantity = fields.Float(
        string="Quantidade",
        default=1.0,
    )

    lot_id = fields.Many2one(
        "stock.lot",
        string="Número de Série / Lote",
    )

    location_id = fields.Many2one(
        "stock.location",
        string="Local de origem",
        default=lambda self: self.env.ref("stock.stock_location_stock", raise_if_not_found=False),
        help=(
            "De onde o produto 'vem' para o RMA.\n"
            "- Garantia do Cliente: normalmente deve ser a Localização de Cliente.\n"
            "- Garantia do Fornecedor / Produção: normalmente WH/Estoque."
        ),
    )

    rma_location_id = fields.Many2one(
        "stock.location",
        string="Local RMA",
        default=lambda self: self.env.ref("bhz_rma.stock_location_rma", raise_if_not_found=False),
        help="Local de estoque específico para produtos com defeito / em RMA.",
    )

    # Auditoria das movimentações que o RMA gerou
    picking_return_id = fields.Many2one(
        "stock.picking",
        string="Transferência (RMA → Estoque)",
        readonly=True,
        copy=False,
    )

    scrap_id = fields.Many2one(
        "stock.scrap",
        string="Sucata (RMA → Sucata)",
        readonly=True,
        copy=False,
    )

    exchange_delivery_move_id = fields.Many2one(
        "stock.move",
        string="Entrega nova ao cliente",
        readonly=True,
        copy=False,
    )

    exchange_return_move_id = fields.Many2one(
        "stock.move",
        string="Retorno defeituoso do cliente",
        readonly=True,
        copy=False,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id.id,
    )

    unit_cost = fields.Monetary(
        string="Custo Unitário",
        currency_field="currency_id",
    )

    total_cost = fields.Monetary(
        string="Custo Total",
        currency_field="currency_id",
        compute="_compute_total_cost",
        store=True,
    )

    note = fields.Text(string="Observações")

    service_order_id = fields.Many2one(
        "bhz.rma.service.order",
        string="Ordem de Serviço",
        help="OS associada quando for Garantia do Cliente.",
    )

    @api.depends("unit_cost", "quantity")
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = (rec.unit_cost or 0.0) * (rec.quantity or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("Novo"):
                vals["name"] = self.env["ir.sequence"].next_by_code("bhz.rma.order") or _("Novo")
        records = super().create(vals_list)
        records._apply_defaults_by_warranty_type()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "warranty_type" in vals and not self.env.context.get("skip_rma_defaults"):
            self._apply_defaults_by_warranty_type()
        return res

    # ---------------------------
    # Defaults inteligentes
    # ---------------------------

    def _apply_defaults_by_warranty_type(self):
        """
        Ajusta defaults conforme o tipo de garantia:
        - Garantia do Cliente: NÃO mexe no WH/Estoque. Origem ideal é Localização de Cliente.
        - Garantia do Fornecedor: normal é RMA → volta pro estoque quando resolvido.
        - Sem garantia: normalmente retira do RMA (sucata) quando finalizar.
        - Produção (interno): pode sair de estoque e ir para RMA (você controla via recebimento).
        """
        default_rma_loc = self.env.ref("bhz_rma.stock_location_rma", raise_if_not_found=False)
        default_stock_loc = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        for rec in self:
            if not rec.rma_location_id and default_rma_loc:
                rec.rma_location_id = default_rma_loc.id
            if not rec.location_id and default_stock_loc:
                rec.location_id = default_stock_loc.id

            if rec.warranty_type == "customer":
                rec.resolution_method = "scrap_from_rma"
            elif rec.warranty_type == "no_warranty":
                rec.resolution_method = "scrap_from_rma"
            elif rec.warranty_type in ("supplier", "production"):
                rec.resolution_method = "return_to_stock"

    # ---------------------------
    # Botões de status
    # ---------------------------

    def action_set_waiting(self):
        for rec in self:
            rec.state = "waiting"

    def action_set_with_supplier(self):
        for rec in self:
            rec.state = "with_supplier"

    def action_set_no_warranty(self):
        for rec in self:
            rec.state = "no_warranty"
            rec.resolution_method = "scrap_from_rma"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_exchange_with_customer(self):
        """
        Troca a peça para o cliente:
        - Sai peça nova do estoque padrão -> cliente.
        - Peça defeituosa retorna do cliente -> Local RMA.
        """
        for rec in self:
            if rec.warranty_type != "customer":
                raise UserError(_("A troca automática é apenas para garantia do cliente."))
            if not rec.partner_id:
                raise UserError(_("Informe o cliente para realizar a troca."))
            if not rec.rma_location_id:
                raise UserError(_("Configure o Local RMA antes da troca."))

            customer_location = rec._get_customer_location()
            if not customer_location:
                raise UserError(_("Não encontrei a localização de cliente para este parceiro."))

            stock_location = rec.location_id or self.env.ref(
                "stock.stock_location_stock", raise_if_not_found=False
            )
            if not stock_location:
                raise UserError(_("Configure o Local de origem (estoque)."))

            # Envia produto novo ao cliente
            if not rec.exchange_delivery_move_id:
                move_new = rec._create_move(
                    stock_location,
                    customer_location,
                    _("Troca RMA %s - Envio ao cliente") % rec.name,
                )
                rec.exchange_delivery_move_id = move_new.id

            # Recebe produto defeituoso de volta
            if not rec.exchange_return_move_id:
                move_defective = rec._create_move(
                    customer_location,
                    rec.rma_location_id,
                    _("Troca RMA %s - Retorno defeituoso") % rec.name,
                    lot=rec.lot_id,
                )
                rec.exchange_return_move_id = move_defective.id

            rec.state = "waiting"

    # ---------------------------
    # Impressão / Email
    # ---------------------------

    def action_print_rma(self):
        self.ensure_one()
        report_action = self.env.ref("bhz_rma.action_report_bhz_rma_order", raise_if_not_found=False)
        if not report_action:
            raise UserError(
                _("O relatório de RMA não está instalado. Reinstale o módulo bhz_rma ou verifique se o arquivo report/rma_report.xml foi carregado.")
            )
        return report_action.report_action(self)

    def action_send_rma_email(self):
        self.ensure_one()
        template = self.env.ref("bhz_rma.email_template_bhz_rma_order", raise_if_not_found=False)
        if not template:
            raise UserError(_("O template de e-mail de RMA não foi encontrado."))
        template.send_mail(self.id, force_send=True)
        return True

    # ---------------------------
    # Estoque: helpers
    # ---------------------------

    def _get_internal_picking_type(self):
        """
        Pega um picking type interno da empresa.
        """
        self.ensure_one()
        picking_type = self.env["stock.picking.type"].search(
            [
                ("code", "=", "internal"),
                ("warehouse_id.company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search([("code", "=", "internal")], limit=1)
        if not picking_type:
            picking_type = self.env.ref("stock.picking_type_internal", raise_if_not_found=False)
        return picking_type

    def _get_scrap_location(self):
        """
        Pega uma localização de sucata válida.
        """
        self.ensure_one()
        loc = self.env.ref("stock.stock_location_scrapped", raise_if_not_found=False)
        if not loc:
            raise UserError(
                _("Configure uma localização de sucata (stock.stock_location_scrapped) para usar o fluxo de RMA.")
            )
        return loc

    def _get_customer_location(self):
        """
        Localização de cliente usada para trocar produto (quando garantia do cliente).
        """
        self.ensure_one()
        partner = self.partner_id
        if partner and partner.property_stock_customer:
            return partner.property_stock_customer
        return self.env["stock.location"].search([("usage", "=", "customer")], limit=1)

    def _create_picking_rma_to_stock(self):
        """
        Cria uma transferência interna (RMA -> Estoque padrão).
        """
        self.ensure_one()

        if not self.rma_location_id:
            raise UserError(_("Defina o Local RMA."))
        if not self.location_id:
            raise UserError(_("Defina o Local de origem (destino ao devolver ao estoque)."))

        picking_type = self._get_internal_picking_type()
        if not picking_type:
            raise UserError(_("Não encontrei um Tipo de Operação 'Transferência Interna'."))

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.rma_location_id.id,
                "location_dest_id": self.location_id.id,
                "company_id": self.company_id.id,
                "origin": self.name,
            }
        )

        move = self.env["stock.move"].create(
            {
                "product_id": self.product_id.id,
                "product_uom_qty": self.quantity,
                "product_uom": self.product_uom_id.id,
                "location_id": self.rma_location_id.id,
                "location_dest_id": self.location_id.id,
                "picking_id": picking.id,
                "company_id": self.company_id.id,
                "description_picking": self.product_id.display_name,
            }
        )

        picking.action_confirm()
        picking.action_assign()

        # cria move line com qty_done
        vals_ml = {
            "picking_id": picking.id,
            "move_id": move.id,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "location_id": self.rma_location_id.id,
            "location_dest_id": self.location_id.id,
            "qty_done": self.quantity,
        }
        if self.lot_id:
            vals_ml["lot_id"] = self.lot_id.id

        self.env["stock.move.line"].create(vals_ml)

        # valida
        picking.button_validate()
        return picking

    def _scrap_from_rma(self):
        """
        Dá baixa do estoque RMA para Sucata.
        """
        self.ensure_one()

        if not self.rma_location_id:
            raise UserError(_("Defina o Local RMA."))

        scrap_location = self._get_scrap_location()
        if not scrap_location:
            raise UserError(_("Não encontrei uma localização de Sucata configurada."))

        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.product_id.id,
                "scrap_qty": self.quantity,
                "product_uom_id": self.product_uom_id.id,
                "location_id": self.rma_location_id.id,
                "scrap_location_id": scrap_location.id,
                "company_id": self.company_id.id,
                "origin": self.name,
                "lot_id": self.lot_id.id if self.lot_id else False,
            }
        )
        scrap.action_validate()
        return scrap

    def _create_move(self, source_location, dest_location, description, lot=None):
        self.ensure_one()
        move_vals = {
            "product_id": self.product_id.id,
            "product_uom_qty": self.quantity,
            "product_uom": self.product_uom_id.id,
            "location_id": source_location.id,
            "location_dest_id": dest_location.id,
            "company_id": self.company_id.id,
            "description_picking": description,
        }
        move = self.env["stock.move"].create(move_vals)
        move._action_confirm()
        move._action_done()
        if lot:
            move.move_line_ids.write({"lot_id": lot.id})
        return move

    # ---------------------------
    # ✅ BOTÃO SOLUCIONADO (com regra de estoque)
    # ---------------------------

    def action_solved(self):
        """
        - Se resolução = return_to_stock: move RMA → Estoque padrão.
        - Se resolução = scrap_from_rma: baixa RMA → Sucata.
        - Se resolução = none: só finaliza.
        """
        for rec in self:
            if rec.state == "cancelled":
                raise UserError(_("Não é possível solucionar um RMA cancelado."))

            resolution = rec.resolution_method or "none"

            # Regras adicionais por tipo de garantia
            if rec.warranty_type == "supplier":
                resolution = "return_to_stock"
            elif rec.warranty_type in ("customer", "no_warranty", "production"):
                resolution = "scrap_from_rma"

            if resolution == "return_to_stock":
                picking = rec._create_picking_rma_to_stock()
                rec.picking_return_id = picking.id
            elif resolution == "scrap_from_rma":
                scrap = rec._scrap_from_rma()
                rec.scrap_id = scrap.id

            rec.state = "solved"
