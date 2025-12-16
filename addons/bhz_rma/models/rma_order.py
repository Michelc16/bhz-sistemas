import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


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
        default=lambda self: self._default_location_id(),
        domain="[('company_id','in',[False, company_id])]",
        check_company=True,
        help=(
            "De onde o produto 'vem' para o RMA.\n"
            "- Garantia do Cliente: normalmente deve ser a Localização de Cliente.\n"
            "- Garantia do Fornecedor / Produção: normalmente WH/Estoque."
        ),
    )

    rma_location_id = fields.Many2one(
        "stock.location",
        string="Local RMA",
        default=lambda self: self._default_rma_location_id(),
        domain="[('usage','=','internal'), ('company_id','=',company_id), ('is_rma_location','=',True)]",
        check_company=True,
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
            company = self._get_company_from_vals(vals)
            vals.setdefault("company_id", company.id)
            if not vals.get("location_id"):
                stock_location = self._get_company_stock_location(company)
                vals["location_id"] = stock_location.id
            if not vals.get("rma_location_id"):
                rma_location = self._ensure_company_rma_location(company)
                vals["rma_location_id"] = rma_location.id
        records = super().create(vals_list)
        records._apply_defaults_by_warranty_type()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "warranty_type" in vals and not self.env.context.get("skip_rma_defaults"):
            self._apply_defaults_by_warranty_type()
        return res

    # ---------------------------
    # Defaults e helpers multiempresa
    # ---------------------------

    @api.model
    def _default_location_id(self):
        company = self.env.company
        location = self._get_company_stock_location(company)
        return location.id if location else False

    @api.model
    def _default_rma_location_id(self):
        company = self.env.company
        location = self._ensure_company_rma_location(company)
        return location.id if location else False

    @api.model
    def _get_company_from_vals(self, vals):
        company_id = vals.get("company_id") or self.env.company.id
        if not company_id:
            raise UserError(_("Defina a empresa do RMA."))
        return self.env["res.company"].browse(company_id)

    @api.model
    def _get_allowed_company_ids(self, company):
        allowed = list(self.env.context.get("allowed_company_ids") or [])
        if company.id not in allowed:
            allowed.append(company.id)
        return allowed

    @api.model
    def _get_company_context(self, company):
        return {
            "force_company": company.id,
            "allowed_company_ids": self._get_allowed_company_ids(company),
        }

    @api.model
    def _get_company_warehouse(self, company):
        Warehouse = self.env["stock.warehouse"].with_context(**self._get_company_context(company)).sudo()
        warehouse = Warehouse.search([("company_id", "=", company.id)], limit=1)
        if not warehouse:
            raise UserError(
                _("Configure um armazém para a empresa %(company)s antes de continuar.")
                % {"company": company.display_name}
            )
        return warehouse.with_env(self.env)

    @api.model
    def _get_company_stock_location(self, company):
        warehouse = self._get_company_warehouse(company)
        stock_location = warehouse.lot_stock_id
        if not stock_location:
            raise UserError(
                _("Configure o local de estoque padrão da empresa %(company)s.") % {"company": company.display_name}
            )
        return stock_location.with_env(self.env)

    @api.model
    def _ensure_company_rma_location(self, company):
        Location = self.env["stock.location"].with_context(**self._get_company_context(company)).sudo()
        rma_location = Location.search(
            [
                ("company_id", "=", company.id),
                ("usage", "=", "internal"),
                ("is_rma_location", "=", True),
            ],
            limit=1,
        )
        if rma_location:
            return rma_location.with_env(self.env)

        parent_location = self._get_company_stock_location(company)
        rma_location = Location.create(
            {
                "name": _("Estoque RMA - %(company)s") % {"company": company.display_name},
                "usage": "internal",
                "company_id": company.id,
                "location_id": parent_location.id,
                "is_rma_location": True,
                "active": True,
            }
        )
        return rma_location.with_env(self.env)

    @api.model
    def _ensure_scrap_location(self, company):
        Location = self.env["stock.location"].with_context(**self._get_company_context(company)).sudo()
        domain = [("scrap_location", "=", True), ("company_id", "=", company.id)]
        scrap_location = Location.search(domain, limit=1)
        if not scrap_location:
            scrap_location = Location.search([("scrap_location", "=", True), ("company_id", "=", False)], limit=1)
        if scrap_location:
            return scrap_location.with_env(self.env)

        warehouse = self._get_company_warehouse(company)
        parent_location = warehouse.view_location_id or self.env.ref(
            "stock.stock_location_locations_virtual", raise_if_not_found=False
        )
        if not parent_location:
            raise UserError(
                _("Configure uma localização pai para criar a sucata da empresa %(company)s.")
                % {"company": company.display_name}
            )
        scrap_location = Location.create(
            {
                "name": _("Sucata - %(company)s") % {"company": company.display_name},
                "usage": "inventory",
                "scrap_location": True,
                "company_id": company.id,
                "location_id": parent_location.id,
                "active": True,
            }
        )
        return scrap_location.with_env(self.env)

    def _ensure_company_locations(self):
        for rec in self:
            company = rec.company_id or self.env.company
            if not company:
                continue
            if not rec.location_id:
                rec.location_id = rec._get_company_stock_location(company).id
            if not rec.rma_location_id:
                rec.rma_location_id = rec._ensure_company_rma_location(company).id

    def _apply_defaults_by_warranty_type(self):
        """
        Ajusta defaults conforme o tipo de garantia:
        - Garantia do Cliente: finaliza sem movimentar estoque por padrão.
        - Garantia do Fornecedor: volta para o estoque padrão ao finalizar.
        - Sem garantia / Produção: baixa do RMA via sucata.
        """
        self._ensure_company_locations()
        for rec in self:
            if rec.warranty_type == "customer":
                rec.resolution_method = "none"
            elif rec.warranty_type in ("no_warranty", "production"):
                rec.resolution_method = "scrap_from_rma"
            else:
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
            rec._ensure_company_locations()
            if rec.warranty_type != "customer":
                raise UserError(_("A troca automática é apenas para garantia do cliente."))
            if not rec.partner_id:
                raise UserError(_("Informe o cliente para realizar a troca."))
            if not rec.rma_location_id:
                raise UserError(_("Configure o Local RMA antes da troca."))

            customer_location = rec._get_customer_location()
            if not customer_location:
                raise UserError(_("Não encontrei a localização de cliente para este parceiro."))

            stock_location = rec.location_id
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
            report_action = self.env["ir.actions.report"].search(
                [("report_name", "=", "bhz_rma.report_rma_document")],
                limit=1,
            )
        if not report_action:
            _logger.error(
                "RMA report action is missing for order %s (company %s).",
                self.id,
                self.company_id.display_name,
            )
            raise UserError(
                _(
                    "O relatório de RMA não está instalado. Reinstale o módulo bhz_rma ou verifique se o arquivo report/rma_report.xml foi carregado."
                )
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
        Recupera o tipo de operação interna (multiempresa).
        """
        self.ensure_one()
        picking_type_env = self.env["stock.picking.type"].with_context(
            force_company=self.company_id.id,
            allowed_company_ids=self.company_id.ids,
        )
        picking_type = picking_type_env.search(
            [("code", "=", "internal"), ("company_id", "=", self.company_id.id)],
            limit=1,
        )
        if not picking_type:
            warehouse = (
                self.env["stock.warehouse"]
                .with_context(force_company=self.company_id.id, allowed_company_ids=self.company_id.ids)
                .search([("company_id", "=", self.company_id.id)], limit=1)
            )
            if warehouse and warehouse.int_type_id:
                picking_type = warehouse.int_type_id

        if not picking_type:
            picking_type = picking_type_env.search(
                [("code", "=", "internal"), ("company_id", "in", [False, self.company_id.id])],
                limit=1,
            )

        if not picking_type:
            picking_type = self.env.ref("stock.picking_type_internal", raise_if_not_found=False)

        if not picking_type:
            raise UserError(
                _(
                    "Configure um Tipo de Operação 'Transferência interna' para a empresa %(company)s antes de continuar.",
                    company=self.company_id.display_name,
                )
            )
        return picking_type.sudo()

    def _get_scrap_location(self):
        """
        Pega uma localização de sucata válida.
        """
        self.ensure_one()
        scrap_location = self._ensure_scrap_location(self.company_id)
        if not scrap_location:
            raise UserError(
                _("Configure uma localização de sucata para usar o fluxo de RMA na empresa %(company)s.")
                % {"company": self.company_id.display_name}
            )
        return scrap_location

    def _get_customer_location(self):
        """
        Localização de cliente usada para trocar produto (quando garantia do cliente).
        """
        self.ensure_one()
        partner = self.partner_id
        if partner and partner.property_stock_customer:
            partner_location = partner.property_stock_customer
            if partner_location.company_id and partner_location.company_id != self.company_id:
                partner_location = False
            else:
                return partner_location
        Location = self.env["stock.location"].with_context(**self._get_company_context(self.company_id))
        return Location.search(
            [
                ("usage", "=", "customer"),
                ("company_id", "in", [False, self.company_id.id]),
            ],
            limit=1,
        )

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
            rec._ensure_company_locations()
            if rec.state == "cancelled":
                raise UserError(_("Não é possível solucionar um RMA cancelado."))

            resolution = rec.resolution_method or "none"

            # Regras adicionais por tipo de garantia
            if rec.warranty_type == "supplier":
                resolution = "return_to_stock"
            elif rec.warranty_type in ("no_warranty", "production"):
                resolution = "scrap_from_rma"
            elif rec.warranty_type == "customer" and resolution == "return_to_stock":
                resolution = "none"

            if resolution == "return_to_stock":
                picking = rec._create_picking_rma_to_stock()
                rec.picking_return_id = picking.id
            elif resolution == "scrap_from_rma":
                scrap = rec._scrap_from_rma()
                rec.scrap_id = scrap.id

            rec.state = "solved"
