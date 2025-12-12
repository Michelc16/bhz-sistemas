from odoo import api, fields, models


class BhzDreTemplateLine(models.Model):
    _name = 'bhz.dre.template.line'
    _description = 'Template de linha da DRE'
    _order = 'sequence, id'

    name = fields.Char('Descrição', required=True)
    sequence = fields.Integer('Sequência', default=10)
    code = fields.Char('Código técnico')

    parent_id = fields.Many2one(
        'bhz.dre.template.line',
        string='Linha pai',
    )
    child_ids = fields.One2many(
        'bhz.dre.template.line',
        'parent_id',
        string='Sub-linhas',
    )

    level = fields.Integer('Nível', default=1)

    line_type = fields.Selection(
        [
            ('title', 'Título'),
            ('normal', 'Linha normal'),
            ('subtotal', 'Subtotal'),
        ],
        string='Tipo de linha',
        default='normal',
        required=True,
    )

    # 1 = somar, -1 = subtrair
    sign = fields.Integer('Sinal (+1 / -1)', default=1)

    account_ids = fields.Many2many(
        'account.account',
        string='Contas contábeis',
    )

    show_on_report = fields.Boolean('Mostrar no relatório', default=True)
