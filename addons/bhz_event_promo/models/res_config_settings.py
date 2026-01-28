from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_featured_carousel_autoplay = fields.Boolean(
        related="website_id.bhz_featured_carousel_autoplay",
        readonly=False,
        string="Autoplay do carrossel de destaques",
    )
    bhz_featured_carousel_interval_ms = fields.Integer(
        related="website_id.bhz_featured_carousel_interval_ms",
        readonly=False,
        string="Intervalo do carrossel (ms)",
    )
    bhz_featured_carousel_refresh_ms = fields.Integer(
        related="website_id.bhz_featured_carousel_refresh_ms",
        readonly=False,
        string="Atualização do carrossel (ms)",
    )
