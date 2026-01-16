# -*- coding: utf-8 -*-
from odoo import fields, models


class GuiaBHPreference(models.Model):
    _name = "guiabh.preference"
    _description = "Preferências do usuário GuiaBH"
    _order = "id desc"
    _table_args = (
        models.Constraint(
            "guiabh_preference_user_website_unique",
            "unique(user_id, website_id)",
        ),
    )

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    website_id = fields.Many2one(
        "website",
        default=lambda self: self.env["website"].get_current_website(),
        required=True,
        ondelete="cascade",
    )
    category_ids = fields.Many2many("guiabh.event.category", string="Categorias de interesse")
    region_ids = fields.Many2many("guiabh.region", string="Regiões de interesse")
