# -*- coding: utf-8 -*-
from odoo import fields, models


class GuiaBHLead(models.Model):
    _name = "guiabh.lead"
    _description = "Lead GuiaBH"
    _order = "create_date desc"

    name = fields.Char("Nome", required=True)
    email = fields.Char("E-mail", required=True)
    category_ids = fields.Many2many("guiabh.event.category", string="Interesses (categorias)")
    website_id = fields.Many2one("website", default=lambda self: self.env["website"].get_current_website())
    consent_lgpd = fields.Boolean("Aceito receber novidades (LGPD)", default=False)
