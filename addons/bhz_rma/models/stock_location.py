from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    is_rma_location = fields.Boolean(
        string="Local de RMA",
        help="Marcador auxiliar para identificar localizações usadas no fluxo de RMA.",
    )
    is_rma_scrap_location = fields.Boolean(
        string="Local de sucata do RMA",
        help="Identifica as localizações de sucata criadas automaticamente pelo módulo de RMA.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_rma_location") and not vals.get("company_id"):
                vals["company_id"] = self.env.context.get("force_company") or self.env.company.id
            if vals.get("is_rma_scrap_location") and not vals.get("company_id"):
                vals["company_id"] = self.env.context.get("force_company") or self.env.company.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_rma_location") or vals.get("is_rma_scrap_location"):
            company = self.env.context.get("force_company") or self.env.company.id
            for location in self:
                if (location.is_rma_location or location.is_rma_scrap_location) and not location.company_id:
                    location.company_id = company
        return res
