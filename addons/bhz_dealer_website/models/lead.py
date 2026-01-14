# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    dealer_car_id = fields.Many2one("bhz.dealer.car", string="Carro (Dealer)")

    @api.model
    def _dealer_source(self):
        Source = self.env["utm.source"].sudo()
        source = Source.search([("name", "=", "Site Dealer")], limit=1)
        if not source:
            source = Source.create({"name": "Site Dealer"})
        return source
