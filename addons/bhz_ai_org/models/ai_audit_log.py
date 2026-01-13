# -*- coding: utf-8 -*-
from odoo import fields, models


class BhzAiAuditLog(models.Model):
    _name = "bhz.ai.audit.log"
    _description = "AI Audit Log"
    _order = "finished_at desc, started_at desc"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    task_id = fields.Many2one("bhz.ai.task", ondelete="set null")
    action_id = fields.Many2one("bhz.ai.task.action", ondelete="set null")
    agent_id = fields.Many2one("bhz.ai.agent", ondelete="set null")
    tool_id = fields.Many2one("bhz.ai.tool", ondelete="set null")
    tool_code = fields.Char()
    run_as_user_id = fields.Many2one("res.users")
    params_json = fields.Text()
    status = fields.Selection([
        ("success", "Success"),
        ("failed", "Failed"),
    ], default="success")
    result_text = fields.Text()
    error_text = fields.Text()
    started_at = fields.Datetime()
    finished_at = fields.Datetime()
