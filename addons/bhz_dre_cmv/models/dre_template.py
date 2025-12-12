# -*- coding: utf-8 -*-

from odoo import fields, models


class BhzDreTemplate(models.Model):
    _name = "bhz.dre.template"
    _description = "Template de DRE"
    _order = "name"

    name = fields.Char(string="Nome", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        "bhz.dre.template.line",
        "template_id",
        string="Linhas",
    )

    def name_get(self):
        result = []
        for template in self:
            display = "%s (%s)" % (template.name, template.company_id.name)
            result.append((template.id, display))
        return result


class BhzDreTemplateLine(models.Model):
    _name = "bhz.dre.template.line"
    _description = "Linha do Template da DRE"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "bhz.dre.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Descrição", required=True)
    code = fields.Char(
        string="Código interno",
        required=True,
        help="Identificador utilizado para localizar a linha na DRE.",
    )
    line_type = fields.Selection(
        [
            ("detail", "Detalhe"),
            ("revenue", "Receita"),
            ("expense", "Despesa"),
            ("subtotal", "Subtotal"),
        ],
        string="Tipo",
        required=True,
        default="detail",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        related="template_id.company_id",
        store=True,
        readonly=True,
    )
    account_ids = fields.Many2many(
        "account.account",
        "bhz_dre_template_line_account_rel",
        "line_id",
        "account_id",
        string="Contas contábeis",
        help="Contas somadas nesta linha.",
    )
    note = fields.Text(string="Observações")
