# -*- coding: utf-8 -*-

from odoo import fields, models, _


class BhzDreReport(models.Model):
    _name = "bhz.dre.report"
    _description = "Relatório de DRE"
    _order = "date_from desc, date_to desc, id desc"

    name = fields.Char(string="Nome", required=True, copy=False, default=lambda self: _("Novo"))
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    date_from = fields.Date(string="Data inicial", required=True)
    date_to = fields.Date(string="Data final", required=True)
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("calculated", "Calculado"),
        ],
        default="draft",
        string="Status",
    )
    line_ids = fields.One2many(
        "bhz.dre.report.line",
        "report_id",
        string="Linhas",
    )

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref("bhz_dre_cmv.action_bhz_dre_print_report").report_action(self)


class BhzDreReportLine(models.Model):
    _name = "bhz.dre.report.line"
    _description = "Linha do relatório de DRE"
    _order = "sequence, id"

    report_id = fields.Many2one(
        "bhz.dre.report",
        string="Relatório",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Descrição", required=True)
    amount = fields.Monetary(string="Valor")
    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        related="report_id.currency_id",
        store=True,
        readonly=True,
    )
