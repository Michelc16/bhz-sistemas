from odoo import fields, models

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    bhz_provider = fields.Selection([
        ("manual", "Manual (Preço fixo)"),
        ("superfrete", "SuperFrete")
    ], default="manual")