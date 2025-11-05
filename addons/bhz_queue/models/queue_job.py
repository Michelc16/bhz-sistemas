from odoo import api, fields, models
import json

class BhzQueueJob(models.Model):
    _name = "bhz.queue.job"
    _description = "BHZ Queue Job"
    _order = "create_date asc"

    name = fields.Char(required=True)
    state = fields.Selection([
        ("pending", "Pending"),
        ("done", "Done"),
        ("error", "Error")
    ], default="pending", required=True)
    model = fields.Char(required=True)
    method = fields.Char(required=True)
    args_json = fields.Text(default="[]")
    kwargs_json = fields.Text(default="{}")
    last_error = fields.Text()

    def run_job(self):
        for job in self:
            try:
                recs = self.env[job.model]
                args = json.loads(job.args_json or "[]")
                kwargs = json.loads(job.kwargs_json or "{}")
                getattr(recs, job.method)(*args, **kwargs)
                job.state = "done"
            except Exception as e: # noqa
                job.state = "error"
                job.last_error = str(e)
    @api.model
    def cron_run_pending(self, limit=50):
        jobs = self.search([("state", "=", "pending")], limit=limit)
        jobs.run_job()
        return True