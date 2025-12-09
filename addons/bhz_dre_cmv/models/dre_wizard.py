# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from calendar import monthrange
from datetime import date


class BhzDreWizard(models.TransientModel):
    _name = "bhz.dre.wizard"
    _description = "Assistente para geração de DRE"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
    )
    year = fields.Integer(
        "Ano",
        required=True,
        default=lambda self: date.today().year,
    )
    month = fields.Selection(
        [
            ("1", "Janeiro"),
            ("2", "Fevereiro"),
            ("3", "Março"),
            ("4", "Abril"),
            ("5", "Maio"),
            ("6", "Junho"),
            ("7", "Julho"),
            ("8", "Agosto"),
            ("9", "Setembro"),
            ("10", "Outubro"),
            ("11", "Novembro"),
            ("12", "Dezembro"),
        ],
        string="Mês",
        required=True,
        default=lambda self: str(date.today().month),
    )

    def action_generate_dre(self):
        self.ensure_one()
        year = self.year
        month = int(self.month)

        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        report = self.env["bhz.dre.report"].create_from_template(
            first_day,
            last_day,
            self.company_id,
        )

        action = self.env.ref("bhz_dre_cmv.action_bhz_dre_report").read()[0]
        action["res_id"] = report.id
        action["views"] = [(self.env.ref("bhz_dre_cmv.view_bhz_dre_report_form").id, "form")]
        return action
