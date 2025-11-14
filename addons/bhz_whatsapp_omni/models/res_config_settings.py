from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bhz_wa_public_base = fields.Char(string='URL pública do Odoo (Webhook)')

    def set_values(self):
        res = super().set_values()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('bhz_wa.public_base', self.bhz_wa_public_base or '')
        return res

    def get_values(self):
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()
        res.update(bhz_wa_public_base=icp.get_param('bhz_wa.public_base'))
        return res
