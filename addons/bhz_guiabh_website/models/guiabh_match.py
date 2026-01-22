from odoo import fields, models
from ._mixins import guiabh_base_fields


class GuiaBHMatch(models.Model):
    _name = "guiabh.match"
    _description = "GuiaBH Match"
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
        "website.slug.mixin",
    ]
    _order = "match_datetime desc"

    name = fields.Char(required=True)
    description = fields.Html()
    category_id = fields.Many2one("guiabh.category", string="Categoria", ondelete="set null")
    match_datetime = fields.Datetime(string="Data/Hora")
    venue = fields.Char(string="Local")

    locals().update(guiabh_base_fields())

    _sql_constraints = [
        ("guiabh_match_slug_company_uniq", "unique(slug, company_id)", "Slug deve ser único por empresa."),
    ]

    def _slug_name(self):
        return self.name
