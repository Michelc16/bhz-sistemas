from odoo import api, fields, models

CM_IN_METER = 100
ML_IN_CUBIC_METER = 1_000_000


class ProductTemplate(models.Model):
    _inherit = "product.template"

    height_cm = fields.Float(string="Altura (cm)", digits="Product Unit of Measure")
    length_cm = fields.Float(string="Comprimento (cm)", digits="Product Unit of Measure")
    width_cm = fields.Float(string="Largura (cm)", digits="Product Unit of Measure")
    height_m = fields.Float(
        string="Altura (m)",
        compute="_compute_dimensions_in_meters",
        inverse="_inverse_dimensions_in_meters",
        store=True,
        digits="Product Unit of Measure",
    )
    length_m = fields.Float(
        string="Comprimento (m)",
        compute="_compute_dimensions_in_meters",
        inverse="_inverse_dimensions_in_meters",
        store=True,
        digits="Product Unit of Measure",
    )
    width_m = fields.Float(
        string="Largura (m)",
        compute="_compute_dimensions_in_meters",
        inverse="_inverse_dimensions_in_meters",
        store=True,
        digits="Product Unit of Measure",
    )
    measurement_brl_display = fields.Char(
        string="Medidas formatadas (AxCxL)",
        compute="_compute_measurement_brl_display",
        store=True,
        help="Mostra as dimensões no formato brasileiro (Altura x Comprimento x Largura em cm).",
    )
    volume_ml = fields.Float(
        string="Volume (ml)",
        compute="_compute_volume_ml",
        inverse="_inverse_volume_ml",
        store=True,
        digits="Product Unit of Measure",
        help="Conversão direta do volume padrão (m³) para mililitros.",
    )

    @api.depends("height_cm", "length_cm", "width_cm")
    def _compute_dimensions_in_meters(self):
        for product in self:
            product.height_m = (product.height_cm or 0.0) / CM_IN_METER
            product.length_m = (product.length_cm or 0.0) / CM_IN_METER
            product.width_m = (product.width_cm or 0.0) / CM_IN_METER

    def _inverse_dimensions_in_meters(self):
        for product in self:
            product.height_cm = (product.height_m or 0.0) * CM_IN_METER
            product.length_cm = (product.length_m or 0.0) * CM_IN_METER
            product.width_cm = (product.width_m or 0.0) * CM_IN_METER

    @api.depends("height_cm", "length_cm", "width_cm")
    def _compute_measurement_brl_display(self):
        for product in self:
            if product.height_cm or product.length_cm or product.width_cm:
                product.measurement_brl_display = "{} x {} x {} cm".format(
                    self._format_dimension(product.height_cm),
                    self._format_dimension(product.length_cm),
                    self._format_dimension(product.width_cm),
                )
            else:
                product.measurement_brl_display = False

    @staticmethod
    def _format_dimension(value):
        value = value or 0.0
        # Strip trailing zeros while keeping at most 2 decimals for readability
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
        return formatted or "0"

    @api.depends("volume")
    def _compute_volume_ml(self):
        for product in self:
            product.volume_ml = (product.volume or 0.0) * ML_IN_CUBIC_METER

    def _inverse_volume_ml(self):
        for product in self:
            product.volume = (product.volume_ml or 0.0) / ML_IN_CUBIC_METER
