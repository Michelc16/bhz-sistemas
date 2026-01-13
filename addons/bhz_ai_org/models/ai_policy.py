# -*- coding: utf-8 -*-
from odoo import fields, models

class BhzAiPolicy(models.Model):
    _name = "bhz.ai.policy"
    _description = "AI Policy"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    # Governança
    require_approval_high_risk = fields.Boolean(default=True)
    require_approval_over_amount = fields.Boolean(default=True)
    amount_limit = fields.Monetary(default=500.0)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)

    # Web / internet
    web_allowlist_domains = fields.Text(
        help="Um domínio por linha. Ex: sympla.com.br\ninstagram.com"
    )
    web_block_private_ips = fields.Boolean(default=True)

    # Segurança operacional
    forbid_delete = fields.Boolean(default=True, help="Se ligado, tools de delete devem exigir aprovação.")
