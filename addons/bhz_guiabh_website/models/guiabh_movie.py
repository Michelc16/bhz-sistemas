from odoo import api, fields, models
from ._mixins import guiabh_base_fields, slugify_value


class GuiaBHMovie(models.Model):
    _name = "guiabh.movie"
    _description = "GuiaBH Movie"
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
    ]
    _order = "release_date desc, name"

    name = fields.Char(required=True)
    description = fields.Html()
    category_id = fields.Many2one("guiabh.category", string="Categoria", ondelete="set null")
    release_date = fields.Date(string="Estreia")
    duration_minutes = fields.Integer(string="Duração (min)")

    locals().update(guiabh_base_fields())

    _sql_constraints = [
        ("guiabh_movie_slug_company_uniq", "unique(slug, company_id)", "Slug deve ser único por empresa."),
    ]

    @api.model
    def create(self, vals):
        if not vals.get("slug") and vals.get("name"):
            vals["slug"] = slugify_value(vals["name"])
        return super().create(vals)
