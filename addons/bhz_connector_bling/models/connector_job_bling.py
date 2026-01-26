# -*- coding: utf-8 -*-
import time
from odoo import models


class BhzConnectorJobBling(models.Model):
    _inherit = "bhz.connector.job"

    def _run_job(self):
        for job in self:
            if job.account_id.connector_type != "bling":
                continue
            time.sleep(0.1)
            job.account_id.message_post(body=f"Job {job.job_type} executado (simulado) no Bling.")
