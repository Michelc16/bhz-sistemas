# -*- coding: utf-8 -*-
import logging
import os

from odoo import api, models

_logger = logging.getLogger(__name__)


class BhzWaConfigSync(models.AbstractModel):
    _name = "bhz.wa.config.sync"
    _description = "Sync Starter Service Params from ENV"

    @api.model
    def action_sync_starter_defaults(self):
        base_url = (os.getenv("ODOO_STARTER_BASE_URL") or "https://bhz-wa-starter.onrender.com").rstrip("/")
        secret = os.getenv("ODOO_WEBHOOK_SECRET")

        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("starter_service.base_url", base_url)
        _logger.info("[bhz_whatsapp_omni][cron] starter_service.base_url => %s", base_url)

        if secret:
            icp.set_param("starter_service.secret", secret)
            _logger.info("[bhz_whatsapp_omni][cron] starter_service.secret atualizado")
