# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class BhzAiAgent(models.Model):
    _name = "bhz.ai.agent"
    _description = "AI Agent"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "role_id desc, name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)

    role_id = fields.Many2one("bhz.ai.role", required=True, tracking=True)
    manager_agent_id = fields.Many2one("bhz.ai.agent", tracking=True, help="Agente superior direto (opcional).")

    # O usuário Odoo que o agente “vira” ao executar ações.
    run_as_user_id = fields.Many2one(
        "res.users", required=True, tracking=True,
        help="As ações serão executadas com as permissões deste usuário."
    )

    policy_id = fields.Many2one("bhz.ai.policy", required=True)

    tool_ids = fields.Many2many("bhz.ai.tool", string="Allowed Tools")

    # LLM config (por agente ou herdado do sistema)
    llm_provider = fields.Selection([
        ("system", "Use System Default"),
        ("openai_compatible", "OpenAI-compatible"),
        ("ollama", "Ollama"),
        ("disabled", "Disabled"),
    ], default="system", required=True)

    model_name = fields.Char(default="gpt-4o-mini", help="Nome do modelo no provider (se aplicável).")
    system_prompt = fields.Text(help="Prompt base do agente (identidade + regras).")

    autonomy_level = fields.Selection([
        ("suggest", "Suggest Only (no execute)"),
        ("execute_low", "Execute Low-Risk"),
        ("execute_all", "Execute All Allowed (subject to approvals)"),
    ], default="execute_low", required=True)

    def check_ready(self):
        for agent in self:
            if not agent.tool_ids:
                raise UserError("Agente sem tools liberadas.")
            if not agent.run_as_user_id:
                raise UserError("Agente sem usuário para executar ações.")
            if agent.llm_provider == "disabled":
                raise UserError("LLM do agente está desabilitado.")
