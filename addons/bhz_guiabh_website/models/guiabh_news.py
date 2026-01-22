from odoo import api, fields, models
from ._mixins import guiabh_base_fields, slugify_value


class GuiaBHNews(models.Model):
    _name = "guiabh.news"
    _description = "GuiaBH News"
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
    ]
    _order = "publish_date desc, name"

    name = fields.Char(required=True)
    description = fields.Html(string="Conteúdo")
    category_id = fields.Many2one("guiabh.category", string="Categoria", ondelete="set null")
    publish_date = fields.Date(string="Publicação")
    author_name = fields.Char(string="Autor")

    locals().update(guiabh_base_fields())

    _sql_constraints = [
        ("guiabh_news_slug_company_uniq", "unique(slug, company_id)", "Slug deve ser único por empresa."),
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
