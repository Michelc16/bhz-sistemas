# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GuiaBHSyncService(models.AbstractModel):
    _name = "bhz.guiabh.sync.service"
    _description = "Serviço de sincronização GuiaBH"

    def run_scheduled_sync(self):
        """Orquestra sincronizações das fontes opcionais, tolerante a falhas."""
        sources = [
            ("bhz_event_promo", "event.event", "action_sync_all_now"),
            ("bhz_cineart", "guiabh.cineart.movie", "action_sync_all_now"),
            ("bhz_football_agenda", "bhz.football.match", "action_sync_all_now"),
            ("bhz_city_places", "bhz.place", "action_sync_all_now"),
        ]
        for module_name, model_name, method_name in sources:
            if not self._module_installed(module_name):
                continue
            Model = self._safe_model(model_name)
            if not Model:
                _logger.info("GuiaBH sync skip: model %s not found", model_name)
                continue
            try:
                if hasattr(Model, method_name):
                    getattr(Model, method_name)()
                    _logger.info("GuiaBH sync ok: %s.%s", model_name, method_name)
                elif hasattr(Model, "cron_sync"):
                    Model.cron_sync()
                    _logger.info("GuiaBH sync ok: %s.cron_sync", model_name)
                else:
                    _logger.info("GuiaBH sync no-op: %s has no sync method", model_name)
            except Exception as exc:
                _logger.warning("GuiaBH sync failed for %s: %s", model_name, exc)
                # do not raise to avoid crashing cron workers
                continue

    def _module_installed(self, module_name):
        module = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", module_name), ("state", "=", "installed")], limit=1)
        )
        return bool(module)

    def _safe_model(self, model_name):
        try:
            return self.env[model_name].sudo()
        except KeyError:
            return None
