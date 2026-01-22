from odoo import fields, models
from ._mixins import guiabh_base_fields


class GuiaBHEvent(models.Model):
    _name = "guiabh.event"
    _description = "GuiaBH Event"
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
        "website.slug.mixin",
    ]
    _order = "start_datetime desc, name"

    name = fields.Char(required=True)
    description = fields.Html()
    category_id = fields.Many2one("guiabh.category", string="Categoria", ondelete="set null")
    start_datetime = fields.Datetime(string="Início")
    end_datetime = fields.Datetime(string="Fim")
    location = fields.Char(string="Local")

    locals().update(guiabh_base_fields())

    _sql_constraints = [
        ("guiabh_event_slug_company_uniq", "unique(slug, company_id)", "Slug deve ser único por empresa."),
    ]

    def _slug_name(self):
        return self.name
