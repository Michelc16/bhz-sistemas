# -*- coding: utf-8 -*-
from odoo import api, fields, models


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

    @api.model
    def _ensure_company_categories(self, company=False):
        """Garantir que cada empresa tenha os códigos padrão (now/premiere/soon)."""
        company = company or self.env.company
        if not company:
            return
        company_id = company.id
        templates = self.sudo().with_context(active_test=False).search([("company_id", "=", False)])
        if not templates:
            return
        existing_codes = set(
            self.sudo()
            .with_context(active_test=False)
            .search([("company_id", "=", company_id)])
            .mapped("code")
        )
        for template in templates:
            if template.code in existing_codes:
                continue
            template.copy(
                {
                    "company_id": company_id,
                    "active": True,
                }
            )
