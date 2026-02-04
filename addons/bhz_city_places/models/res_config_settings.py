from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_city_places_enabled = fields.Boolean(
        related="website_id.bhz_city_places_enabled",
        readonly=False,
        string="Ativar Locais (/lugares) neste Website",
    )

    def set_values(self):
        super().set_values()
        self.website_id._bhz_city_places_sync_menu()
