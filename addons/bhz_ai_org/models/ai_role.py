# -*- coding: utf-8 -*-
from odoo import api, fields, models

class BhzAiRole(models.Model):
    _name = "bhz.ai.role"
    _description = "AI Role (Organograma)"
    _order = "level desc, name"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    level = fields.Integer(required=True, default=10, help="Quanto maior, mais alto no organograma.")
    parent_id = fields.Many2one("bhz.ai.role", index=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("bhz.ai.role", "parent_id")

    description = fields.Text()
