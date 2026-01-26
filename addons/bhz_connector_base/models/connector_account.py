# -*- coding: utf-8 -*-
from odoo import fields, models


class BhzConnectorAccount(models.Model):
    _name = "bhz.connector.account"
    _description = "Conta de Conector ERP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True)
    seller_id = fields.Many2one("bhz.marketplace.seller", required=True, index=True, tracking=True)
    connector_type = fields.Selection([
        ("tiny", "Tiny"),
        ("bling", "Bling"),
        ("omie", "Omie"),
        ("custom", "Custom"),
    ], required=True, default="tiny", tracking=True)
    api_key = fields.Char(tracking=True)
    api_secret = fields.Char(tracking=True)
    base_url = fields.Char(tracking=True)
    state = fields.Selection([
        ("draft", "Rascunho"),
        ("connected", "Conectado"),
        ("error", "Erro"),
    ], default="draft", tracking=True)
    last_sync_at = fields.Datetime()
