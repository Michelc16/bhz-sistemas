# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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

    @api.constrains("code", "company_id")
    def _check_unique_code_per_company(self):
        for rec in self:
            if not rec.code:
                continue
            domain = [
                ("id", "!=", rec.id),
                ("code", "=", rec.code),
                ("company_id", "=", rec.company_id.id if rec.company_id else False),
            ]
            if self.with_context(active_test=False).search_count(domain):
                raise ValidationError(
                    _("O código da categoria deve ser único por empresa.")
                )
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
