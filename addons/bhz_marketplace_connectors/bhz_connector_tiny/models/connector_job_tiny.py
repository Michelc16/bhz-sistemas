# -*- coding: utf-8 -*-
import time
from odoo import models


class BhzConnectorJobTiny(models.Model):
    _inherit = "bhz.connector.job"

    def _run_job(self):
        for job in self:
            if job.account_id.connector_type != "tiny":
                continue
            # simula execução
            time.sleep(0.1)
            # poderia logar em chatter da account
            job.account_id.message_post(body=f"Job {job.job_type} executado (simulado) no Tiny.")
