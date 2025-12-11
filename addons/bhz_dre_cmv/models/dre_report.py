from odoo import api, fields, models, _
from datetime import datetime
class BhzDreReport(models.Model):
    _name = "bhz.dre.report"
    _description = "Relatório de DRE"
    _order = "date_from desc, company_id"

    name = fields.Char("Descrição", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date("Data inicial", required=True)
    date_to = fields.Date("Data final", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    line_ids = fields.One2many(
        "bhz.dre.report.line",
        "report_id",
        string="Linhas DRE",
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

    @api.model
    def create_from_template(self, date_from, date_to, company):
        """Gera um relatório de DRE para o período/empresa definidos."""
        template_lines = self.env["bhz.dre.template.line"].search(
            [("company_id", "=", company.id)], order="sequence, id"
        )
        if not template_lines:
            raise ValueError(_("Não há linhas de template de DRE configuradas."))

        name = _("DRE %s - %s (%s)") % (
            date_from.strftime("%d/%m/%Y"),
            date_to.strftime("%d/%m/%Y"),
            company.name,
        )

        report = self.create(
            {
                "name": name,
                "company_id": company.id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )

        # cria linhas do relatório com base no template
        for tmpl in template_lines:
            self.env["bhz.dre.report.line"].create(
                {
                    "report_id": report.id,
                    "template_line_id": tmpl.id,
                    "name": tmpl.name,
                    "code": tmpl.code,
                    "sequence": tmpl.sequence,
                    "level": tmpl.level,
                }
            )

        report._compute_lines_values()
        report.state = "calculated"
        return report

    def _compute_lines_values(self):
        """Aplica os métodos de cálculo para cada linha (accounts, cmv, fórmula)."""
        for report in self:
            # índice para facilitar fórmulas (code -> line)
            lines_by_code = {l.code: l for l in report.line_ids if l.code}

            for line in report.line_ids:
                tmpl = line.template_line_id
                amount = 0.0

                if tmpl.compute_method == "accounts":
                    amount = report._compute_amount_from_accounts(tmpl)
                elif tmpl.compute_method == "cmv":
                    amount = report._compute_cmv_period()
                elif tmpl.compute_method == "formula" and tmpl.formula:
                    amount = report._compute_amount_from_formula(
                        tmpl.formula, lines_by_code
                    )
                else:
                    # manual = mantém valor (pode ser preenchido depois)
                    amount = line.amount

                # CORRIGIDO: converte o sign (string) para int antes de multiplicar
                sign = int(tmpl.sign or "1")
                line.amount = (amount or 0.0) * sign

    def _compute_amount_from_accounts(self, tmpl_line):
        """Soma o saldo das contas configuradas na linha, no período da DRE."""
        self.ensure_one()
        if not tmpl_line.account_ids:
            return 0.0

        domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("account_id", "in", tmpl_line.account_ids.ids),
            ("parent_state", "=", "posted"),
        ]

        aml = self.env["account.move.line"].read_group(
            domain,
            ["debit", "credit"],
            []
        )
        if not aml:
            return 0.0

        debit = aml[0].get("debit", 0.0) or 0.0
        credit = aml[0].get("credit", 0.0) or 0.0
        # receita normalmente é credit > debit; despesa ao contrário
        return debit - credit

    def _compute_cmv_period(self):
        """
        Calcula o CMV do período usando stock.valuation.layer.

        Lógica:
        - Considera valuation layers da empresa
        - Dentro do período (date >= date_from, date <= date_to)
        - Somente movimentos de saída (quantity < 0)
        - CMV = - soma dos valores (value) desses layers
        """
        self.ensure_one()
        svl = self.env["stock.valuation.layer"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("create_date", ">=", fields.Datetime.to_datetime(self.date_from)),
                ("create_date", "<=", fields.Datetime.to_datetime(self.date_to)),
                ("quantity", "<", 0),
            ]
        )
        if not svl:
            return 0.0

        total_value = sum(svl.mapped("value") or [0.0])
        # em geral, saídas têm value negativo -> CMV positivo
        return -total_value

    def _compute_amount_from_formula(self, formula, lines_by_code):
        """
        Fórmula simples usando códigos de linha.

        Exemplo de fórmula:
            RECEITA_BRUTA - DEVOLUCAO - IMPOSTOS_VENDAS

        Isso não executa Python arbitrário, só substitui códigos por valores.
        """
        if not formula:
            return 0.0

        # monta um dicionário seguro com os valores
        local_dict = {}
        for code, line in lines_by_code.items():
            local_dict[code] = line.amount or 0.0

        expr = formula
        for code in local_dict:
            expr = expr.replace(code, f"local_dict['{code}']")

        try:
            return eval(expr, {"__builtins__": {}}, {"local_dict": local_dict})
        except Exception:
            return 0.0


class BhzDreReportLine(models.Model):
    _name = "bhz.dre.report.line"
    _description = "Linha de DRE calculada"
    _order = "sequence, id"

    report_id = fields.Many2one(
        "bhz.dre.report",
        string="Relatório",
        required=True,
        ondelete="cascade",
    )
    template_line_id = fields.Many2one(
        "bhz.dre.template.line",
        string="Linha de template",
        ondelete="set null",
    )

    name = fields.Char("Descrição", required=True)
    code = fields.Char("Código")
    sequence = fields.Integer("Ordem", default=10)
    level = fields.Selection(
        [
            ("title", "Título / Seção"),
            ("subtotal", "Subtotal"),
            ("line", "Linha de detalhe"),
        ],
        string="Nível",
        default="line",
    )
    amount = fields.Monetary("Valor", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        related="report_id.currency_id",
        store=True,
        readonly=True,
    )
