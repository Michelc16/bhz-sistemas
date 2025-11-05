from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def create(self, vals_list):
        # garante que todos os registros recebam company_id se vierem sem
        helper = self.env["bhz.auto.company.mixin"]
        vals_list = helper._bhz_default_company_vals(vals_list)
        return super(ResPartner, self).create(vals_list)
