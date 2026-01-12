# -*- coding: utf-8 -*-
import json
import traceback
from odoo import api, fields, models
from odoo.exceptions import UserError

class BhzAiTask(models.Model):
    _name = "bhz.ai.task"
    _description = "AI Task Queue"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, default="AI Task", tracking=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)

    requester_user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    agent_id = fields.Many2one("bhz.ai.agent", required=True)
    policy_id = fields.Many2one(related="agent_id.policy_id", store=True, readonly=True)

    state = fields.Selection([
        ("draft", "Draft"),
        ("planned", "Planned"),
        ("waiting_approval", "Waiting Approval"),
        ("running", "Running"),
        ("done", "Done"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    user_input = fields.Text(required=True)
    plan_json = fields.Text(help="Plano (JSON) com lista de ações que serão executadas.")
    result_text = fields.Text()
    error_text = fields.Text()

    approval_required = fields.Boolean(default=False)
    approved_by_id = fields.Many2one("res.users")
    approved_on = fields.Datetime()

    action_ids = fields.One2many("bhz.ai.task.action", "task_id", string="Actions")

    def action_plan(self):
        for task in self:
            task.agent_id.check_ready()
            prompt = (
                "Você deve criar um PLANO em JSON com a chave 'actions' (lista). "
                "Cada action deve ter: tool_code, params (obj), rationale (texto curto). "
                "Respeite: só use tool_code permitido ao agente.\n\n"
                f"Solicitação do usuário:\n{task.user_input}\n"
            )
            text = self.env["bhz.ai.providers"].llm_generate(task.agent_id, prompt)
            task.plan_json = text
            task.state = "planned"
            task._materialize_actions_from_plan()

    def _materialize_actions_from_plan(self):
        for task in self:
            # tenta parsear JSON “na unha”, mas aceita se o LLM vier com texto extra
            raw = (task.plan_json or "").strip()
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                raise UserError("Plano não veio em JSON válido.")
            data = json.loads(raw[start:end+1])
            actions = data.get("actions") or []
            task.action_ids.unlink()
            Tool = self.env["bhz.ai.tool"].sudo()
            allowed = set(task.agent_id.tool_ids.mapped("code"))

            approval_needed = False
            vals_list = []
            for a in actions:
                code = a.get("tool_code")
                params = a.get("params") or {}
                if code not in allowed:
                    raise UserError(f"Tool '{code}' não permitida para este agente.")
                tool = Tool.search([("code", "=", code), ("active", "=", True)], limit=1)
                if not tool:
                    raise UserError(f"Tool '{code}' não encontrada/ativa.")
                if tool.requires_approval and task.policy_id.require_approval_high_risk:
                    approval_needed = True

                vals_list.append({
                    "task_id": task.id,
                    "sequence": len(vals_list) + 1,
                    "tool_id": tool.id,
                    "params_json": json.dumps(params, ensure_ascii=False),
                    "rationale": a.get("rationale") or "",
                    "state": "pending",
                })

            task.action_ids = [(0, 0, v) for v in vals_list]
            task.approval_required = approval_needed
            task.state = "waiting_approval" if approval_needed else "planned"

    def action_approve(self):
        for task in self:
            if task.state != "waiting_approval":
                continue
            task.approved_by_id = self.env.user
            task.approved_on = fields.Datetime.now()
            task.state = "planned"

    def action_run_now(self):
        for task in self:
            task._run_task()

    def _run_task(self):
        self.ensure_one()
        task = self

        if task.agent_id.autonomy_level == "suggest":
            raise UserError("Este agente está em modo Suggest Only (não executa ações).")

        if task.state not in ("planned",):
            raise UserError("Task não está pronta para execução (precisa estar Planned).")

        task.state = "running"
        run_env = self.env(user=task.agent_id.run_as_user_id.id, company=task.company_id)

        try:
            outputs = []
            for action in task.action_ids.sorted("sequence"):
                if action.state in ("done",):
                    continue
                out = action._execute(run_env)
                outputs.append(out)

            task.result_text = "\n\n".join(outputs) if outputs else "OK"
            task.state = "done"
        except Exception as e:
            task.error_text = (str(e) + "\n\n" + traceback.format_exc())[:5000]
            task.state = "failed"

    @api.model
    def cron_process_queue(self):
        tasks = self.search([("state", "=", "planned")], limit=10)
        for t in tasks:
            t._run_task()


class BhzAiTaskAction(models.Model):
    _name = "bhz.ai.task.action"
    _description = "AI Task Action"
    _order = "sequence asc"

    task_id = fields.Many2one("bhz.ai.task", required=True, ondelete="cascade")
    sequence = fields.Integer(default=1)
    tool_id = fields.Many2one("bhz.ai.tool", required=True)
    params_json = fields.Text()
    rationale = fields.Text()

    state = fields.Selection([
        ("pending", "Pending"),
        ("running", "Running"),
        ("done", "Done"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ], default="pending")

    result_text = fields.Text()
    error_text = fields.Text()

    def _execute(self, run_env):
        self.ensure_one()
        action = self
        action.state = "running"

        params = {}
        if action.params_json:
            params = json.loads(action.params_json)

        tool = action.tool_id
        Model = run_env[tool.model_name]

        if not hasattr(Model, tool.method_name):
            raise UserError(f"Tool inválida: {tool.model_name}.{tool.method_name}")

        # chamada controlada
        try:
            res = getattr(Model, tool.method_name)(**params)
            action.result_text = str(res)[:5000]
            action.state = "done"
            return f"[{tool.code}] {action.result_text}"
        except Exception as e:
            action.error_text = (str(e) + "\n" + traceback.format_exc())[:5000]
            action.state = "failed"
            raise
