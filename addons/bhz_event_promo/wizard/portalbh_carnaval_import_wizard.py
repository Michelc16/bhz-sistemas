# -*- coding: utf-8 -*-

from odoo import _, fields, models


class PortalBHCarnavalImportWizard(models.TransientModel):
    """Inicia uma importação do PortalBH (Carnaval 2026 - Blocos de Rua).

    Importação roda em *background* via cron para não travar a tela e evitar timeout
    do proxy do Odoo.sh.
    """

    _name = "bhz.portalbh.carnaval.import.wizard"
    _description = "Importador PortalBH - Carnaval 2026 (Blocos de Rua)"

    source_url = fields.Char(
        string="URL base",
        default="https://portalbelohorizonte.com.br/carnaval/2026/programacao/bloco-de-rua",
        required=True,
    )
    max_pages = fields.Integer(string="Máx. páginas", default=50)
    update_existing = fields.Boolean(string="Atualizar existentes", default=True)
    default_duration_hours = fields.Float(string="Duração padrão (h)", default=3.0)

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    website_id = fields.Many2one(
        "website",
        string="Website",
        help="Opcional. Se definido, os eventos importados ficam vinculados a este website.",
        domain="[(\"company_id\", \"=\", company_id)]",
    )

    def action_import_portalbh(self):
        self.ensure_one()

        job = self.env["bhz.portalbh.carnaval.import.job"].sudo().create(
            {
                "source_url": (self.source_url or "").strip(),
                "max_pages": int(self.max_pages or 1),
                "update_existing": bool(self.update_existing),
                "default_duration_hours": float(self.default_duration_hours or 3.0),
                "company_id": self.company_id.id,
                "website_id": self.website_id.id if self.website_id else False,
            }
        )
        job.action_enqueue()

        # Abre o job para acompanhar o status/log
        return {
            "type": "ir.actions.act_window",
            "name": _("Importação PortalBH"),
            "res_model": "bhz.portalbh.carnaval.import.job",
            "res_id": job.id,
            "view_mode": "form",
            "target": "current",
        }
