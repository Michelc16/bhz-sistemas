# -*- coding: utf-8 -*-
from odoo import fields, models


class BhzMarketplaceDashboard(models.Model):
    _name = "bhz.marketplace.dashboard"
    _description = "Dashboard do BHZ Marketplace"

    name = fields.Char(default="BHZ Marketplace")
