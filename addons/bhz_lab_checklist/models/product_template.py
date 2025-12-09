from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_lab_equipment = fields.Boolean(
        string="Equipamento de Laboratório (PC/Notebook)",
        help="Se marcado, ao vender este produto será gerado um checklist para o laboratório."
    )
    lab_checklist_template_id = fields.Many2one(
        "lab.checklist.template",
        string="Template de Checklist",
        help="Template padrão de checklist para este produto."
    )
