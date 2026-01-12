# -*- coding: utf-8 -*-
from odoo import fields, models

class BhzAiAuditLog(models.Model):
    _name = "bhz.ai.audit.log"
    _description = "Audit log de execuções AI"
    _order = "create_date desc"

    task_action_id = fields.Many2one('bhz.ai.task.action', ondelete='set null')
    tool_code = fields.Char()
    params_json = fields.Text()
    user_id = fields.Many2one('res.users')
    company_id = fields.Many2one('res.company')
    status = fields.Selection([
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='done')
    message = fields.Text()
    executed_on = fields.Datetime(default=lambda self: fields.Datetime.now())
