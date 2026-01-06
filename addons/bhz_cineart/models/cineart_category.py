# -*- coding: utf-8 -*-
from odoo import fields, models


class GuiabhCineartCategory(models.Model):
    _name = "guiabh.cineart.category"
    _description = "Categoria (Cineart)"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        ("cineart_category_code_unique", "unique(code)", "O código da categoria deve ser único."),
    ]
