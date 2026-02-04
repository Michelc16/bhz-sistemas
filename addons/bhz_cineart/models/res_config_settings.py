from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_cineart_enabled = fields.Boolean(
        related="website_id.bhz_cineart_enabled",
        readonly=False,
        string="Ativar Cineart (/cineart) neste Website",
    )

    def set_values(self):
        super().set_values()
        self.website_id._bhz_cineart_sync_menu()
