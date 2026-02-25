from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_featured_carousel_autoplay = fields.Boolean(
        string="Autoplay do carrossel de destaques",
        config_parameter="bhz_event_promo.bhz_featured_carousel_autoplay",
    )
    bhz_featured_carousel_interval_ms = fields.Integer(
        string="Intervalo do carrossel (ms)",
        config_parameter="bhz_event_promo.bhz_featured_carousel_interval_ms",
    )
    bhz_featured_carousel_refresh_ms = fields.Integer(
        string="Atualização do carrossel (ms)",
        config_parameter="bhz_event_promo.bhz_featured_carousel_refresh_ms",
    )
