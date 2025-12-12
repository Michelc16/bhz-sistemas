# -*- coding: utf-8 -*-

from datetime import date

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models


class BhzDreWizard(models.TransientModel):
    _name = "bhz.dre.wizard"
    _description = "Assistente para geração da DRE"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string="Data inicial", required=True)
    date_to = fields.Date(string="Data final", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = date.today()
        first_day = today.replace(day=1)
        last_day = first_day + relativedelta(months=1, days=-1)
        res.setdefault("date_from", first_day)
        res.setdefault("date_to", last_day)
        return res

    def _get_move_lines(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("move_id.state", "=", "posted"),
        ]
        return self.env["account.move.line"].search(domain)

    def _build_line_values(self):
        move_lines = self._get_move_lines()
        income_lines = move_lines.filtered(lambda ml: ml.account_id.internal_group == "income")
        expense_lines = move_lines.filtered(lambda ml: ml.account_id.internal_group == "expense")

        income_total = sum(-line.balance for line in income_lines)
        expense_total = sum(line.balance for line in expense_lines)
        result = income_total - expense_total

        line_values = [
            (0, 0, {"sequence": 10, "name": _("Receitas"), "amount": income_total}),
            (0, 0, {"sequence": 20, "name": _("Despesas"), "amount": expense_total}),
            (0, 0, {"sequence": 30, "name": _("Resultado do Período"), "amount": result}),
        ]
        return line_values

    def action_generate(self):
        self.ensure_one()
        report_model = self.env["bhz.dre.report"]
        report = report_model.search(
            [
                ("company_id", "=", self.company_id.id),
                ("date_from", "=", self.date_from),
                ("date_to", "=", self.date_to),
            ],
            limit=1,
        )
        name = _("DRE %(start)s a %(end)s") % {
            "start": fields.Date.to_string(self.date_from),
            "end": fields.Date.to_string(self.date_to),
        }
        if report:
            report.write({"name": name, "state": "draft"})
        else:
            report = report_model.create(
                {
                    "name": name,
                    "company_id": self.company_id.id,
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                }
            )

        line_commands = [(5, 0, 0)] + self._build_line_values()
        report.write({"line_ids": line_commands, "state": "calculated"})

        return {
            "type": "ir.actions.act_window",
            "name": _("Relatório DRE"),
            "res_model": "bhz.dre.report",
            "view_mode": "form",
            "res_id": report.id,
            "target": "current",
        }
