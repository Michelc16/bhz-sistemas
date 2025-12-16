from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    is_rma_location = fields.Boolean(
        string="Local de RMA",
        help="Marcador auxiliar para identificar localizações usadas no fluxo de RMA.",
    )
