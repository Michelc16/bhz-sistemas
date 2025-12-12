from odoo import api, fields, models, _


class BhzDreWizard(models.TransientModel):
    _name = 'bhz.dre.wizard'
    _description = 'Assistente para gerar DRE'

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date('Data inicial', required=True)
    date_to = fields.Date('Data final', required=True)

    def action_generate(self):
        self.ensure_one()
        report = self.env['bhz.dre.report'].create_from_period(
            self.date_from,
            self.date_to,
            self.company_id,
        )
        action = self.env.ref('bhz_dre_cmv.action_bhz_dre_report').read()[0]
        action['res_id'] = report.id
        action['views'] = [
            (self.env.ref('bhz_dre_cmv.view_bhz_dre_report_form').id, 'form')
        ]
        return action
