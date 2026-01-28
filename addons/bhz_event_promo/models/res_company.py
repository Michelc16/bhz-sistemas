from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    bhz_featured_carousel_autoplay = fields.Boolean(
        string="Autoplay do carrossel de destaques",
        default=True,
        help="Habilita reprodução automática dos destaques.",
    )
    bhz_featured_carousel_interval_ms = fields.Integer(
        string="Intervalo do carrossel (ms)",
        default=5000,
        help="Tempo entre slides do carrossel de destaques.",
    )
    bhz_featured_carousel_refresh_ms = fields.Integer(
        string="Atualização do carrossel (ms)",
        default=0,
        help="Frequência de atualização automática do carrossel de destaques. 0 desabilita.",
    )
