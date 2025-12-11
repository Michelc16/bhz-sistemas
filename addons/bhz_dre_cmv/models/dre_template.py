from odoo import fields, models
class BhzDreTemplateLine(models.Model):
    _name = "bhz.dre.template.line"
    _description = "Template de Linha da DRE"
    _order = "sequence, id"

    name = fields.Char("Descrição", required=True)
    code = fields.Char(
        "Código técnico",
        required=True,
        help="Identificador interno (ex: RECEITA_BRUTA, CMV_TOTAL, EBITDA).",
    )
    sequence = fields.Integer("Ordem", default=10)
    level = fields.Selection(
        [
            ("title", "Título / Seção"),
            ("subtotal", "Subtotal"),
            ("line", "Linha de detalhe"),
        ],
        string="Nível",
        default="line",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
    )

    compute_method = fields.Selection(
        [
            ("accounts", "Por contas contábeis"),
            ("cmv", "CMV do período"),
            ("formula", "Fórmula"),
            ("manual", "Manual"),
        ],
        string="Método de Cálculo",
        default="accounts",
        required=True,
    )

    account_ids = fields.Many2many(
        "account.account",
        "bhz_dre_template_line_account_rel",
        "line_id",
        "account_id",
        string="Contas contábeis",
        help="Contas usadas para somar/subtrair nesta linha.",
    )

    # CORRIGIDO: valores da selection como string (Odoo 19 exige str)
    sign = fields.Selection(
        [
            ("1", "Positivo (Receita)"),
            ("-1", "Negativo (Custo/Despesa)"),
        ],
        string="Sinal",
        default="-1",
        help="Define se o valor desta linha entra como positivo ou negativo na DRE.",
    )

    formula = fields.Char(
        "Fórmula (opcional)",
        help=(
            "Usado somente se o método for 'Fórmula'. "
            "Exemplo: RECEITA_LIQ = RECEITA_BRUTA - DEVOLUCAO - IMPOSTOS_VENDAS"
        ),
    )

    parent_id = fields.Many2one(
        "bhz.dre.template.line",
        string="Linha pai",
        ondelete="set null",
    )
    child_ids = fields.One2many(
        "bhz.dre.template.line",
        "parent_id",
        string="Linhas filhas",
    )

    note = fields.Text("Observações")
