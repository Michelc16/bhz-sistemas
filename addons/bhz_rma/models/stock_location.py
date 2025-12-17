from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    is_rma_location = fields.Boolean(
        string="Local de RMA",
        help="Marcador auxiliar para identificar localizações usadas no fluxo de RMA.",
    )
    is_rma_scrap_location = fields.Boolean(
        string="Local de sucata do RMA",
        help="Identifica as localizações de sucata criadas automaticamente pelo módulo de RMA.",
    )
