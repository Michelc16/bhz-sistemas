from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_football_agenda_api_token = fields.Char(
        string="Token API da Agenda de Futebol",
        config_parameter="bhz_football_agenda.api_token",
        help="Token usado para autenticar integrações externas que enviam jogos via API.",
    )

    bhz_football_agenda_enabled = fields.Boolean(
        related="website_id.bhz_football_agenda_enabled",
        readonly=False,
        string="Ativar Agenda de Futebol neste Website",
    )

    def set_values(self):
        super().set_values()
        self.website_id._bhz_football_sync_menu()
