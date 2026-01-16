# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GuiaBHFav(models.Model):
    _name = "guiabh.favorite"
    _description = "GuiaBH Favorite"
    _order = "create_date desc"
    _table_args = (
        models.Constraint(
            "guiabh_favorite_unique",
            "unique(user_id, website_id, res_model, res_id)",
        ),
    )

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    website_id = fields.Many2one(
        "website",
        default=lambda self: self.env["website"].get_current_website() or self.env.ref("website.default_website"),
        required=True,
        ondelete="cascade",
    )
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)

    @api.constrains("res_model")
    def _check_model(self):
        allowed = {"guiabh.event", "guiabh.place"}
        for rec in self:
            if rec.res_model not in allowed:
                raise ValidationError("Modelo não permitido para favoritos.")
