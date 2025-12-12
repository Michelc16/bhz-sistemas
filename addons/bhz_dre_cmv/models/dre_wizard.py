from datetime import date

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class BhzDreWizard(models.TransientModel):
    _name = "bhz.dre.wizard"
    _description = "Assistente para gerar DRE BHZ"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string="Data inicial", required=True)
    date_to = fields.Date(string="Data final", required=True)
    template_id = fields.Many2one(
        "bhz.dre.template", string="Template de DRE", required=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = date.today()
        first_day = today.replace(day=1)
        last_day = first_day + relativedelta(months=1, days=-1)
        if "date_from" in fields_list:
            res.setdefault("date_from", first_day)
        if "date_to" in fields_list:
            res.setdefault("date_to", last_day)
        return res

    def action_generate_dre(self):
        """Calcula a DRE e abre o relatório transitório."""
        self.ensure_one()
        template = self.template_id

        report_vals = {
            "company_id": self.company_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "template_id": template.id,
            "state": "calculated",
        }
        report = self.env["bhz.dre.report"].create(report_vals)

        aml_domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("move_id.state", "=", "posted"),
        ]
        all_move_lines = self.env["account.move.line"].search(aml_domain)

        code_to_amount = {}

        for line in template.line_ids:
            amount = 0.0
            if not line.is_total:
                lines_for_accounts = all_move_lines.filtered(
                    lambda l: l.account_id in line.account_ids
                )
                amount = sum(lines_for_accounts.mapped("balance"))
                if line.sign == "negative":
                    amount = -amount
            else:
                if line.total_source_codes:
                    codes = [c.strip() for c in line.total_source_codes.split(",") if c.strip()]
                    for code in codes:
                        amount += code_to_amount.get(code, 0.0)

            code_to_amount[line.code or str(line.id)] = amount

            if abs(amount) < 0.0001:
                continue

            self.env["bhz.dre.report.line"].create(
                {
                    "report_id": report.id,
                    "sequence": line.sequence,
                    "name": line.name,
                    "amount": amount,
                }
            )

        return {
            "type": "ir.actions.act_window",
            "res_model": "bhz.dre.report",
            "view_mode": "form",
            "res_id": report.id,
            "target": "current",
        }
