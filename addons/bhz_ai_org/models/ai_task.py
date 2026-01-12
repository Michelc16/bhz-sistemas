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
    router_agent_id = fields.Many2one("bhz.ai.agent", string="Roteador (CEO)")
    assigned_agent_id = fields.Many2one("bhz.ai.agent", string="Agente designado")
    policy_id = fields.Many2one(related="agent_id.policy_id", store=True, readonly=True)
    routing_json = fields.Text(help="Retorno bruto do roteador (JSON)")

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
    memory_context = fields.Text(help="Contexto de memória usado no planejamento.")
    result_text = fields.Text()
    error_text = fields.Text()

    has_destructive_actions = fields.Boolean(default=False, help="Há tools destrutivas neste plano.")
    approval_required = fields.Boolean(default=False)
    approved_by_id = fields.Many2one("res.users")
    approved_on = fields.Datetime()

    action_ids = fields.One2many("bhz.ai.task.action", "task_id", string="Actions")

    def _get_execution_agent(self):
        self.ensure_one()
        return self.assigned_agent_id or self.agent_id

    @api.model
    def _is_destructive_tool(self, tool):
        if not tool:
            return False
        if tool.is_destructive:
            return True
        code = (tool.code or "").lower()
        method = (tool.method_name or "").lower()
        for kw in ("unlink", "delete", "destroy", "remove"):
            if kw in code or kw in method:
                return True
        return False

    def _route_task(self):
        for task in self:
            router = task.router_agent_id or task.agent_id
            exec_agent = task.agent_id
            routing_payload = {}
            try:
                router.check_ready()
                prompt = (
                    "Você é o agente roteador (CEO). Analise o pedido e responda SOMENTE com JSON no formato:\n"
                    "{ \"delegate_to\": \"agent_code\", \"notes\": \"...\", \"actions\": [] }\n"
                    "- delegate_to: código do agente que deve executar. Se for você mesmo, deixe vazio ou null.\n"
                    "- notes: breve orientação.\n"
                    "- actions: lista sugerida (opcional).\n"
                    "Pedido do usuário:\n"
                    f"{task.user_input}"
                )
                text = self.env["bhz.ai.providers"].llm_generate(router, prompt)
                raw = (text or "").strip()
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1:
                    routing_payload = json.loads(raw[start:end+1])
                else:
                    routing_payload = {}
            except Exception:
                routing_payload = {}

            task.routing_json = json.dumps(routing_payload, ensure_ascii=False)

            delegate_code = routing_payload.get("delegate_to") if isinstance(routing_payload, dict) else None
            if delegate_code:
                delegated = self.env["bhz.ai.agent"].search([
                    ("code", "=", delegate_code),
                    ("company_id", "=", task.company_id.id),
                    ("active", "=", True),
                ], limit=1)
                if delegated:
                    exec_agent = delegated
            task.assigned_agent_id = exec_agent.id

    def action_plan(self):
        for task in self:
            task._route_task()
            exec_agent = task._get_execution_agent()
            exec_agent.check_ready()
            # Buscar memória corporativa antes do planejamento
            memory_tool = self.env["bhz.ai.memory"]
            query = (task.user_input or "")[:200]
            memory_results = memory_tool.search_memory(query=query, limit=5)
            lines = []
            for m in memory_results:
                line = f"- ({m.get('tags') or ''}) {m.get('name')}: {m.get('excerpt') or ''}"
                lines.append(line)
            memory_block = "MEMORY_CONTEXT:\n" + ("\n".join(lines) if lines else "- (none)") + "\n"
            task.memory_context = memory_block
            prompt = (
                "Você deve criar um PLANO em JSON com a chave 'actions' (lista). "
                "Cada action deve ter: tool_code, params (obj), rationale (texto curto). "
                "Respeite: só use tool_code permitido ao agente.\n\n"
                f"{memory_block}\n"
                f"Solicitação do usuário:\n{task.user_input}\n"
            )
            text = self.env["bhz.ai.providers"].llm_generate(exec_agent, prompt)
            task.plan_json = text
            task.state = "planned"
            task._materialize_actions_from_plan(exec_agent)

    def _materialize_actions_from_plan(self, exec_agent=None):
        for task in self:
            exec_agent = exec_agent or task._get_execution_agent()
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
            allowed = set(exec_agent.tool_ids.mapped("code"))

            approval_needed = False
            destructive_found = False
            vals_list = []
            for a in actions:
                code = a.get("tool_code")
                params = a.get("params") or {}
                if code not in allowed:
                    raise UserError(f"Tool '{code}' não permitida para este agente.")
                tool = Tool.search([("code", "=", code), ("active", "=", True)], limit=1)
                if not tool:
                    raise UserError(f"Tool '{code}' não encontrada/ativa.")
                policy = exec_agent.policy_id
                if self._is_destructive_tool(tool):
                    destructive_found = True
                if tool.requires_approval and policy and policy.require_approval_high_risk:
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
            policy = exec_agent.policy_id
            if policy and policy.forbid_delete and destructive_found:
                approval_needed = True
            task.has_destructive_actions = destructive_found
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

        if task.policy_id and task.policy_id.forbid_delete and task.has_destructive_actions and not task.approved_by_id:
            raise UserError("Esta task possui actions destrutivas e exige aprovação prévia.")

        task.state = "running"
        exec_agent = task._get_execution_agent()
        run_env = self.env(user=exec_agent.run_as_user_id.id, company=task.company_id)

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

        log = self.env["bhz.ai.audit.log"].sudo().create({
            "company_id": action.task_id.company_id.id,
            "task_id": action.task_id.id,
            "action_id": action.id,
            "agent_id": action.task_id.assigned_agent_id.id or action.task_id.agent_id.id,
            "tool_id": tool.id,
            "tool_code": tool.code,
            "run_as_user_id": run_env.user.id,
            "params_json": action.params_json,
            "started_at": fields.Datetime.now(),
        })

        try:
            res = getattr(Model, tool.method_name)(**params)
            action.result_text = str(res)[:5000]
            action.state = "done"
            log.write({
                "status": "success",
                "result_text": action.result_text,
                "finished_at": fields.Datetime.now(),
            })
            return f"[{tool.code}] {action.result_text}"
        except Exception as e:
            action.error_text = (str(e) + "\n" + traceback.format_exc())[:5000]
            action.state = "failed"
            log.write({
                "status": "failed",
                "error_text": action.error_text,
                "finished_at": fields.Datetime.now(),
            })
            raise
