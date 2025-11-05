from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    company_type = fields.Selection(
        selection_add=[
            ("supplier", "Fornecedor"),
            ("transporter", "Transportador"),
        ],
    )
    bhz_company_type_internal = fields.Selection(
        selection=[
            ("supplier", "Fornecedor"),
            ("transporter", "Transportador"),
        ],
        default=False,
        copy=False,
    )

    @api.depends("is_company", "bhz_company_type_internal")
    def _compute_company_type(self):
        super()._compute_company_type()
        for partner in self:
            if partner.bhz_company_type_internal:
                partner.company_type = partner.bhz_company_type_internal

    def _write_company_type(self):
        super()._write_company_type()
        for partner in self:
            if partner.company_type in ("supplier", "transporter"):
                partner.bhz_company_type_internal = partner.company_type
                partner.is_company = True
            else:
                partner.bhz_company_type_internal = False

    @api.onchange("company_type")
    def onchange_company_type(self):
        super().onchange_company_type()
        if self.company_type in ("supplier", "transporter"):
            self.bhz_company_type_internal = self.company_type
            self.is_company = True
        else:
            self.bhz_company_type_internal = False
