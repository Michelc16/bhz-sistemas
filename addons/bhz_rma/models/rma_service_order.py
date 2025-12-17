from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BhzRmaServiceOrder(models.Model):
    _name = "bhz.rma.service.order"
    _description = "BHZ RMA - Ordem de Serviço (Garantia Cliente)"
    _order = "create_date desc"

    name = fields.Char(
        string="Ordem de Serviço",
        required=True,
        copy=False,
        default=lambda self: _("Novo"),
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        related="rma_id.company_id",
        store=True,
        readonly=True,
    )

    rma_id = fields.Many2one(
        "bhz.rma.order",
        string="RMA",
        required=True,
        ondelete="cascade",
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Peça / Produto",
        required=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidade",
        required=True,
        default=lambda self: self.env.ref(
            "uom.product_uom_unit", raise_if_not_found=False
        ),
    )

    quantity = fields.Float(
        string="Quantidade",
        default=1.0,
        required=True,
    )

    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("in_progress", "Em andamento"),
            ("done", "Concluída"),
            ("cancelled", "Cancelada"),
        ],
        string="Status",
        default="draft",
        required=True,
    )

    move_defective_id = fields.Many2one(
        "stock.move",
        string="Movimento peça defeituosa",
        readonly=True,
    )

    move_new_id = fields.Many2one(
        "stock.move",
        string="Movimento peça nova",
        readonly=True,
    )

    note = fields.Text(string="Observações")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("Novo"):
                vals["name"] = self.env["ir.sequence"].next_by_code("bhz.rma.service.order") or _("Novo")
        return super().create(vals_list)

    def action_start(self):
        for order in self:
            if order.state != "draft":
                continue
            order.state = "in_progress"

    def action_process_exchange(self):
        for order in self:
            rma = order.rma_id
            if not rma:
                raise UserError(_("Ordem de Serviço não está vinculada a um RMA."))

            if rma.warranty_type != "customer":
                raise UserError(
                    _(
                        "A troca de peça pela Ordem de Serviço só é permitida "
                        "para RMAs com garantia do cliente."
                    )
                )

            if order.move_defective_id or order.move_new_id:
                continue

            if order.quantity <= 0:
                raise UserError(_("A quantidade deve ser maior que zero."))

            if not rma.location_id or not rma.rma_location_id:
                raise UserError(
                    _(
                        "Defina o local de origem e o local de RMA no pedido de RMA antes de processar a OS."
                    )
                )

            rma._ensure_company_locations()
            warehouse = rma._get_company_warehouse(rma.company_id)
            outgoing_type = self._get_picking_type(warehouse, "outgoing")
            incoming_type = self._get_picking_type(warehouse, "incoming")

            customer_location = rma._get_customer_location(order.partner_id or rma.partner_id)
            if not customer_location:
                raise UserError(_("Não encontrei uma localização de cliente para este RMA."))

            move_new = self._create_stock_move(
                picking_type=outgoing_type,
                product=order.product_id,
                quantity=order.quantity,
                uom=order.product_uom_id,
                source_location=rma.location_id,
                dest_location=customer_location,
                order=order,
                description=_("Troca RMA %s - Entrega ao cliente") % order.name,
            )

            move_defective = self._create_stock_move(
                picking_type=incoming_type,
                product=order.product_id,
                quantity=order.quantity,
                uom=order.product_uom_id,
                source_location=customer_location,
                dest_location=rma.rma_location_id,
                order=order,
                description=_("Troca RMA %s - Retorno defeituoso") % order.name,
                lot=rma.lot_id,
            )

            order.move_new_id = move_new.id
            order.move_defective_id = move_defective.id
            order.state = "done"

    def action_cancel(self):
        for order in self:
            if order.state == "done":
                raise UserError(_("Não é possível cancelar uma OS concluída."))
            order.state = "cancelled"

    # ---------------------------
    # Helpers
    # ---------------------------

    def _get_picking_type(self, warehouse, code):
        field_map = {
            "incoming": "in_type_id",
            "outgoing": "out_type_id",
            "internal": "int_type_id",
        }
        picking_type = getattr(warehouse, field_map[code], False)
        if picking_type:
            return picking_type
        allowed = set(self.env.context.get("allowed_company_ids") or [])
        allowed.add(warehouse.company_id.id)
        PickingType = (
            self.env["stock.picking.type"]
            .with_company(warehouse.company_id)
            .with_context(allowed_company_ids=list(allowed))
        )
        picking_type = PickingType.search(
            [("code", "=", code), ("company_id", "=", warehouse.company_id.id)],
            limit=1,
        )
        if not picking_type:
            raise UserError(
                _("Configure um tipo de operação '%(code)s' para a empresa %(company)s antes de continuar.")
                % {"code": code, "company": warehouse.company_id.display_name}
            )
        return picking_type

    def _create_stock_move(
        self,
        picking_type,
        product,
        quantity,
        uom,
        source_location,
        dest_location,
        order,
        description,
        lot=None,
    ):
        Picking = (
            self.env["stock.picking"]
            .with_company(order.company_id)
            .with_context(allowed_company_ids=[order.company_id.id])
        )
        Move = (
            self.env["stock.move"]
            .with_company(order.company_id)
            .with_context(allowed_company_ids=[order.company_id.id])
        )
        MoveLine = (
            self.env["stock.move.line"]
            .with_company(order.company_id)
            .with_context(allowed_company_ids=[order.company_id.id])
        )

        picking = Picking.create(
            {
                "picking_type_id": picking_type.id,
                "location_id": source_location.id,
                "location_dest_id": dest_location.id,
                "company_id": order.company_id.id,
                "origin": order.name,
            }
        )
        move = Move.create(
            {
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": uom.id,
                "location_id": source_location.id,
                "location_dest_id": dest_location.id,
                "picking_id": picking.id,
                "company_id": order.company_id.id,
                "description_picking": description,
                "origin": order.name,
            }
        )
        picking.action_confirm()
        picking.action_assign()
        ml_vals = {
            "picking_id": picking.id,
            "move_id": move.id,
            "product_id": product.id,
            "product_uom_id": uom.id,
            "location_id": source_location.id,
            "location_dest_id": dest_location.id,
            "qty_done": quantity,
            "company_id": order.company_id.id,
        }
        if lot:
            ml_vals["lot_id"] = lot.id
        MoveLine.create(ml_vals)
        picking.with_context(skip_backorder=True).button_validate()
        return move
