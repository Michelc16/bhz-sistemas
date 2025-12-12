from odoo import api, fields, models


class BhzDreReport(models.TransientModel):
    _name = "bhz.dre.report"
    _description = "Relatório DRE BHZ"

    name = fields.Char(string="Nome", default="DRE do Período", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    date_from = fields.Date(string="Data inicial", readonly=True)
    date_to = fields.Date(string="Data final", readonly=True)
    template_id = fields.Many2one(
        "bhz.dre.template", string="Template de DRE", readonly=True
    )
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("calculated", "Calculado"),
        ],
        string="Status",
        default="draft",
        readonly=True,
    )
    line_ids = fields.One2many(
        "bhz.dre.report.line",
        "report_id",
        string="Linhas calculadas",
        readonly=True,
    )

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref("bhz_dre_cmv.action_bhz_dre_print_report").report_action(
            self
        )


class BhzDreReportLine(models.TransientModel):
    _name = "bhz.dre.report.line"
    _description = "Linha de relatório DRE BHZ"
    _order = "sequence, id"

    report_id = fields.Many2one(
        "bhz.dre.report", string="Relatório", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(string="Sequência", default=10)
    name = fields.Char(string="Descrição", required=True)
    amount = fields.Monetary(string="Valor")
    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        related="report_id.company_id.currency_id",
        store=True,
        readonly=True,
    )
