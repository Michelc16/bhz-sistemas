# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LabChecklistTemplate(models.Model):
    _name = "lab.checklist.template"
    _description = "Template de Checklist de Laboratório"

    name = fields.Char("Nome", required=True)
    equipment_type = fields.Selection(
        [
            ("desktop", "Computador"),
            ("notebook", "Notebook"),
            ("generic", "Genérico"),
        ],
        string="Tipo de Equipamento",
        default="generic",
        help="Ajuda a escolher o template automaticamente para PCs/Notebooks.",
    )
    active = fields.Boolean("Ativo", default=True)
    line_ids = fields.One2many(
        "lab.checklist.template.line",
        "template_id",
        string="Itens do Template",
    )


class LabChecklistTemplateLine(models.Model):
    _name = "lab.checklist.template.line"
    _description = "Item de Template de Checklist de Laboratório"
    _order = "sequence, id"

    name = fields.Char("Descrição do Item", required=True)
    sequence = fields.Integer("Sequência", default=10)
    template_id = fields.Many2one(
        "lab.checklist.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )


class LabChecklist(models.Model):
    _name = "lab.checklist"
    _description = "Checklist de Laboratório"
    _order = "create_date desc"

    name = fields.Char("Nome", required=True, default=lambda self: "Checklist")
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Pedido de Venda",
        ondelete="cascade",
    )
    sale_order_line_id = fields.Many2one(
        "sale.order.line",
        string="Linha do Pedido",
        ondelete="set null",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Produto",
        required=True,
    )
    template_id = fields.Many2one(
        "lab.checklist.template",
        string="Template",
    )
    technician_id = fields.Many2one(
        "res.users",
        string="Técnico Responsável",
        help="Técnico que fará os testes.",
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("in_progress", "Em andamento"),
            ("done", "Concluído"),
        ],
        string="Status",
        default="draft",
    )
    line_ids = fields.One2many(
        "lab.checklist.line",
        "checklist_id",
        string="Itens de Checklist",
    )
    notes = fields.Text("Observações Gerais")

    # Botão: colocar em andamento
    def action_start(self):
        for rec in self:
            rec.state = "in_progress"

    # Botão: concluir checklist
    def action_done(self):
        for rec in self:
            rec.state = "done"


class LabChecklistLine(models.Model):
    _name = "lab.checklist.line"
    _description = "Item de Checklist de Laboratório"
    _order = "sequence, id"

    name = fields.Char("Item de Verificação", required=True)
    sequence = fields.Integer("Sequência", default=10)
    checklist_id = fields.Many2one(
        "lab.checklist",
        string="Checklist",
        required=True,
        ondelete="cascade",
    )
    done = fields.Boolean("Concluído")
    notes = fields.Char("Observações")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    lab_checklist_count = fields.Integer(
        string="Nº de Checklists",
        compute="_compute_lab_checklist_count",
    )

    def _compute_lab_checklist_count(self):
        Checklist = self.env["lab.checklist"]
        for order in self:
            order.lab_checklist_count = Checklist.search_count(
                [("sale_order_id", "=", order.id)]
            )

    def action_view_lab_checklists(self):
        self.ensure_one()
        action = self.env.ref("bhz_lab_checklist.action_lab_checklist").read()[0]
        action["domain"] = [("sale_order_id", "=", self.id)]
        action["context"] = {
            "default_sale_order_id": self.id,
        }
        return action

    def _get_default_template_for_product(self, product):
        """Escolhe o template quando o produto não tem um definido."""
        template = product.lab_checklist_template_id
        if template:
            return template

        equipment_type = "generic"
        name = (product.name or "").lower()
        if "note" in name or "notebook" in name or "laptop" in name:
            equipment_type = "notebook"
        elif "pc" in name or "computador" in name or "desktop" in name:
            equipment_type = "desktop"

        template = self.env["lab.checklist.template"].search(
            [
                ("equipment_type", "=", equipment_type),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not template:
            template = self.env["lab.checklist.template"].search(
                [
                    ("equipment_type", "=", "generic"),
                    ("active", "=", True),
                ],
                limit=1,
            )
        return template

    def _create_lab_checklists_from_order(self):
        Checklist = self.env["lab.checklist"]

        for order in self:
            for line in order.order_line:
                product = line.product_id
                if not product or not product.product_tmpl_id.is_lab_equipment:
                    continue

                # Evitar duplicar checklist para a mesma linha
                existing = Checklist.search(
                    [("sale_order_line_id", "=", line.id)],
                    limit=1,
                )
                if existing:
                    continue

                template = self._get_default_template_for_product(product)
                vals = {
                    "name": f"Checklist - {product.display_name} ({order.name})",
                    "sale_order_id": order.id,
                    "sale_order_line_id": line.id,
                    "product_id": product.id,
                    "template_id": template.id if template else False,
                    "state": "draft",
                }
                checklist = Checklist.create(vals)

                # Criar itens com base no template
                if template:
                    lines_vals = []
                    for tline in template.line_ids:
                        lines_vals.append(
                            {
                                "name": tline.name,
                                "sequence": tline.sequence,
                                "checklist_id": checklist.id,
                            }
                        )
                    if lines_vals:
                        self.env["lab.checklist.line"].create(lines_vals)

    def action_confirm(self):
        res = super().action_confirm()
        # Após confirmar o pedido, gerar checklists para equipamentos
        self._create_lab_checklists_from_order()
        return res
