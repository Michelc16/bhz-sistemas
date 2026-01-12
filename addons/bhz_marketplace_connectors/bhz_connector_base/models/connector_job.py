# -*- coding: utf-8 -*-
import json
from odoo import fields, models


class BhzConnectorJob(models.Model):
    _name = "bhz.connector.job"
    _description = "Job de Conector ERP"
    _order = "create_date desc"

    account_id = fields.Many2one("bhz.connector.account", required=True, ondelete="cascade")
    job_type = fields.Selection([
        ("import_products", "Importar produtos"),
        ("sync_stock", "Sincronizar estoque"),
        ("export_orders", "Exportar pedidos"),
    ], required=True)
    state = fields.Selection([
        ("pending", "Pendente"),
        ("running", "Executando"),
        ("done", "Concluído"),
        ("failed", "Falhou"),
    ], default="pending")
    attempts = fields.Integer(default=0)
    error = fields.Text()
    payload_json = fields.Text(help="Dados adicionais para o job")

    def action_run(self):
        for job in self:
            job.state = "running"
            job.attempts += 1
            try:
                # A execução real fica para os módulos específicos
                job._run_job()
                job.state = "done"
            except Exception as e:
                job.error = str(e)
                job.state = "failed"

    def _run_job(self):
        # Base não implementa; módulos filhos sobrescrevem
        raise NotImplementedError("Implementar no conector específico")

    def action_retry(self):
        self.write({"state": "pending", "error": False})

    def payload_dict(self):
        try:
            return json.loads(self.payload_json or "{}")
        except Exception:
            return {}
