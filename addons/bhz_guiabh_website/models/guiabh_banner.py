# -*- coding: utf-8 -*-
from odoo import fields, models


class GuiabhBanner(models.Model):
    _name = "guiabh.banner"
    _description = "Banner GuiaBH"
    _order = "sequence, id"

    name = fields.Char("Título", required=True)
    subtitle = fields.Char("Subtítulo")
    image = fields.Image("Imagem", max_width=1920, max_height=1080)
    link_url = fields.Char("Link")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    date_start = fields.Datetime("Início")
    date_end = fields.Datetime("Fim")
    website_id = fields.Many2one("website", string="Website", ondelete="cascade")
