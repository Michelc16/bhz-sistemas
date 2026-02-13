# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class PortalBHCarnavalImportWizard(models.TransientModel):
    _name = "bhz.portalbh.carnaval.import.wizard"
    _description = "Assistente de Importação - Blocos Carnaval BH (PortalBH)"

    source_url = fields.Char(
        string="URL de origem",
        required=True,
        default="https://portalbelohorizonte.com.br/carnaval",
        help="URL usada como ponto de partida para scraping/importação.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    def action_start_import(self):
        self.ensure_one()
        Job = self.env["bhz.portalbh.carnaval.import.job"].sudo()
        job = Job.create({
            "name": "Importação PortalBH (Carnaval)",
            "source_url": self.source_url,
            "company_id": self.company_id.id,
            "state": "draft",
        })
        _logger.info("[BHZ EVENT PROMO] job criado: %s", job.id)
        # chama método existente no job se existir
        if hasattr(job, "action_run"):
            job.action_run()
        return {"type": "ir.actions.act_window_close"}


class BhzEventImportWizard(models.TransientModel):
    _name = "bhz.event.import.wizard"
    _description = "Assistente de Importação de Eventos"

    source_url = fields.Char(string="URL de origem", required=True)
    company_id = fields.Many2one("res.company", string="Empresa", required=True, default=lambda self: self.env.company)

    def action_start_import(self):
        # placeholder para manter compatibilidade com views existentes
        return {"type": "ir.actions.act_window_close"}
