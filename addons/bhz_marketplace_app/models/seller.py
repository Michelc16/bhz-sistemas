# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzMarketplaceSeller(models.Model):
    _inherit = "bhz.marketplace.seller"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa do marketplace",
        default=lambda self: self.env.company,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Garante que sellers novos herdam a empresa atual quando não informado.
        for vals in vals_list:
            vals.setdefault("company_id", self.env.company.id)
        return super().create(vals_list)
