from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_wa_public_base = fields.Char(
        string="URL pública BHZ WhatsApp",
        config_parameter="bhz_wa.public_base",
        help="Ex: https://seu-dominio.odoo.com. Usado para montar as URLs de webhook.",
    )
