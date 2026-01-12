# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class BhzAiTool(models.Model):
    _name = "bhz.ai.tool"
    _description = "AI Tool Registry"
    _order = "risk_level desc, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    # dispatcher: chama model.method com params json
    model_name = fields.Char(required=True, help="Ex: sale.order")
    method_name = fields.Char(required=True, help="Ex: bhz_ai_create_order")

    description = fields.Text()
    risk_level = fields.Selection([
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ], default="medium", required=True)

    requires_approval = fields.Boolean(default=False)
    sample_params_json = fields.Text(help="Exemplo de params em JSON (para documentação).")

    def validate_callable(self):
        for rec in self:
            Model = self.env.get(rec.model_name)
            if not Model:
                raise UserError(f"Model '{rec.model_name}' não existe.")
            if not hasattr(Model, rec.method_name):
                raise UserError(f"Método '{rec.method_name}' não existe em '{rec.model_name}'.")
