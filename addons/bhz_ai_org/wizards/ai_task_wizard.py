# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class BhzAiTaskWizard(models.TransientModel):
    _name = "bhz.ai.task.wizard"
    _description = "Wizard: Create AI Task"

    agent_id = fields.Many2one("bhz.ai.agent", required=True)
    user_input = fields.Text(required=True, string="Pedido")

    auto_plan = fields.Boolean(default=True, string="Gerar plano automaticamente")
    auto_run = fields.Boolean(default=False, string="Executar automaticamente (se não exigir aprovação)")

    def action_create_task(self):
        self.ensure_one()
        if not self.user_input.strip():
            raise UserError("Informe o pedido.")

        task = self.env["bhz.ai.task"].create({
            "name": "AI Task",
            "agent_id": self.agent_id.id,
            "router_agent_id": self.agent_id.id,
            "user_input": self.user_input,
            "company_id": self.env.company.id,
            "requester_user_id": self.env.user.id,
        })

        if self.auto_plan:
            task.action_plan()
            # se exigir aprovação, vai ficar waiting_approval
            if self.auto_run and task.state == "planned":
                task.action_run_now()

        return {
            "type": "ir.actions.act_window",
            "res_model": "bhz.ai.task",
            "view_mode": "form",
            "res_id": task.id,
            "target": "current",
        }
