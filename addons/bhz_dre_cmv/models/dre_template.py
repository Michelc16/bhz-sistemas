from odoo import api, fields, models


class BhzDreTemplate(models.Model):
    _name = "bhz.dre.template"
    _description = "Template de DRE BHZ"

    name = fields.Char(string="Nome do Template", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        "bhz.dre.template.line",
        "template_id",
        string="Linhas da DRE",
    )

    _sql_constraints = [
        (
            "name_company_unique",
            "unique(name, company_id)",
            "Já existe um template de DRE com esse nome para esta empresa.",
        )
    ]


class BhzDreTemplateLine(models.Model):
    _name = "bhz.dre.template.line"
    _description = "Linha de Template de DRE"
    _order = "sequence, id"

    name = fields.Char(string="Descrição", required=True)
    template_id = fields.Many2one(
        "bhz.dre.template", string="Template", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(string="Sequência", default=10)
    code = fields.Char(
        string="Código",
        help="Código interno para identificar a linha no cálculo.",
    )
    account_ids = fields.Many2many(
        "account.account",
        "bhz_dre_template_line_account_rel",
        "line_id",
        "account_id",
        string="Contas contábeis",
        help="Contas que serão somadas para esta linha.",
    )
    sign = fields.Selection(
        [
            ("positive", "Somar"),
            ("negative", "Subtrair"),
        ],
        string="Sinal",
        default="positive",
        required=True,
    )
    is_total = fields.Boolean(
        string="É totalizador?",
        help="Se marcado, esta linha será calculada a partir de outras linhas de código.",
    )
    total_source_codes = fields.Char(
        string="Códigos de linhas fonte",
        help="Informe códigos de outras linhas separados por vírgula para somar/subtrair neste total.",
    )

    @api.constrains("is_total", "account_ids")
    def _check_accounts_or_total(self):
        for line in self:
            if not line.is_total and not line.account_ids:
                raise ValueError(
                    "Linhas que não são totalizadoras precisam ter ao menos uma conta contábil."
                )
