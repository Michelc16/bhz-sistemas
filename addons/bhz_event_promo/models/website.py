from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    bhz_featured_carousel_autoplay = fields.Boolean(
        string="Autoplay do carrossel de destaques",
        help="Se marcado, o carrossel de destaques roda automaticamente.",
    )
    bhz_featured_carousel_interval_ms = fields.Integer(
        string="Intervalo do carrossel (ms)",
        help="Tempo entre slides do carrossel de destaques.",
    )
    bhz_featured_carousel_refresh_ms = fields.Integer(
        string="Atualização do carrossel (ms)",
        help="Frequência de atualização automática do carrossel. 0 desabilita.",
    )
