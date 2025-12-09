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
        default=lambda self: self.env.company,
        required=True,
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

    @api.model
    def create(self, vals):
        if not vals.get("name") or vals.get("name") == _("Novo"):
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("bhz.rma.service.order")
                or _("Novo")
            )
        return super().create(vals)

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

            customer_location = self.env.ref(
                "stock.stock_location_customers", raise_if_not_found=False
            )
            if not customer_location:
                raise UserError(_("Local de clientes não encontrado."))

            Move = self.env["stock.move"]

            # Peça nova: sai do estoque interno para o cliente
            move_new_vals = {
                "name": "%s - peça nova para cliente" % (order.name,),
                "company_id": order.company_id.id,
                "product_id": order.product_id.id,
                "product_uom": order.product_uom_id.id,
                "product_uom_qty": order.quantity,
                "location_id": rma.location_id.id,
                "location_dest_id": customer_location.id,
                "origin": order.name,
            }
            move_new = Move.create(move_new_vals)
            move_new._action_confirm()
            move_new._action_done()

            # Peça defeituosa: entra no estoque RMA
            move_defective_vals = {
                "name": "%s - peça defeituosa para RMA" % (order.name,),
                "company_id": order.company_id.id,
                "product_id": order.product_id.id,
                "product_uom": order.product_uom_id.id,
                "product_uom_qty": order.quantity,
                "location_id": customer_location.id,
                "location_dest_id": rma.rma_location_id.id,
                "origin": order.name,
            }
            move_defective = Move.create(move_defective_vals)
            move_defective._action_confirm()
            move_defective._action_done()

            order.move_new_id = move_new.id
            order.move_defective_id = move_defective.id
            order.state = "done"

    def action_cancel(self):
        for order in self:
            if order.state == "done":
                raise UserError(_("Não é possível cancelar uma OS concluída."))
            order.state = "cancelled"
