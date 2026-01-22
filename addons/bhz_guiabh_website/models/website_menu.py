from odoo import fields, models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    guiabh_category_id = fields.Many2one("guiabh.category", string="GuiaBH Categoria", ondelete="cascade")
