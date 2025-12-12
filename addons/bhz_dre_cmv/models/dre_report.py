from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BhzDreReport(models.Model):
    _name = 'bhz.dre.report'
    _description = 'Relatório de DRE'
    _order = 'date_from desc, id desc'

    name = fields.Char('Nome', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date('Data inicial', required=True)
    date_to = fields.Date('Data final', required=True)

    line_ids = fields.One2many(
        'bhz.dre.report.line',
        'report_id',
        string='Linhas',
    )

    state = fields.Selection(
        [('draft', 'Rascunho'), ('calculated', 'Calculado')],
        string='Status',
        default='draft',
        required=True,
    )

    @api.model
    def create_from_period(self, date_from, date_to, company):
        template_lines = self.env['bhz.dre.template.line'].search([], order='sequence')
        if not template_lines:
            raise UserError(_(
                'Nenhum template de DRE encontrado.\n'
                'Configure em Financeiro → Relatórios → DRE → Template de DRE.'
            ))

        report = self.create({
            'name': _('DRE %s - %s') % (date_from, date_to),
            'company_id': company.id,
            'date_from': date_from,
            'date_to': date_to,
            'state': 'draft',
        })

        aml_domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        MoveLine = self.env['account.move.line']

        for tmpl in template_lines:
            amount = 0.0
            if tmpl.account_ids:
                domain = aml_domain + [('account_id', 'in', tmpl.account_ids.ids)]
                # soma de balance (crédito negativo, débito positivo)
                amount = sum(MoveLine.search(domain).mapped('balance'))

            self.env['bhz.dre.report.line'].create({
                'report_id': report.id,
                'template_id': tmpl.id,
                'name': tmpl.name,
                'sequence': tmpl.sequence,
                'amount': amount * (tmpl.sign or 1),
                'level': tmpl.level,
                'line_type': tmpl.line_type,
            })

        report.state = 'calculated'
        return report


class BhzDreReportLine(models.Model):
    _name = 'bhz.dre.report.line'
    _description = 'Linha de relatório DRE'
    _order = 'sequence, id'

    report_id = fields.Many2one(
        'bhz.dre.report',
        string='Relatório',
        required=True,
        ondelete='cascade',
    )
    template_id = fields.Many2one(
        'bhz.dre.template.line',
        string='Template',
    )
    name = fields.Char('Descrição', required=True)
    sequence = fields.Integer('Sequência', default=10)

    amount = fields.Monetary('Valor', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        related='report_id.company_id.currency_id',
        store=True,
        readonly=True,
    )

    level = fields.Integer('Nível', default=1)

    line_type = fields.Selection(
        [
            ('title', 'Título'),
            ('normal', 'Linha'),
            ('subtotal', 'Subtotal'),
        ],
        string='Tipo de linha',
        default='normal',
    )
