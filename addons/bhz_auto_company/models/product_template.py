from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _name = "product.template"

    def create(self, vals):
        vals = self.env["bhz.auto.company.mixin"]._bhz_default_company_vals(vals)
        return super(ProductTemplate, self).create(vals)
