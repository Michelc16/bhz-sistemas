from odoo import api, fields, models
from ._mixins import guiabh_base_fields, slugify_value


class GuiaBHPlace(models.Model):
    _name = "guiabh.place"
    _description = "GuiaBH Place"
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
    ]
    _order = "name"

    name = fields.Char(required=True)
    description = fields.Html()
    category_id = fields.Many2one("guiabh.category", string="Categoria", ondelete="set null")
    address = fields.Char(string="Endereço")
    phone = fields.Char(string="Telefone")

    locals().update(guiabh_base_fields())

    _sql_constraints = [
        ("guiabh_place_slug_company_uniq", "unique(slug, company_id)", "Slug deve ser único por empresa."),
    ]

    @api.model
    def create(self, vals):
        if not vals.get("slug") and vals.get("name"):
            vals["slug"] = slugify_value(vals["name"])
        return super().create(vals)

    def write(self, vals):
        if not vals.get("slug") and vals.get("name"):
            vals["slug"] = slugify_value(vals["name"])
        return super().write(vals)
