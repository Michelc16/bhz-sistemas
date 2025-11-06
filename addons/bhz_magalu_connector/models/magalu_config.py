from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

CLIENT_ID_PARAM = "bhz_magalu.client_id"
CLIENT_SECRET_PARAM = "bhz_magalu.client_secret"
REDIRECT_PARAM = "bhz_magalu.redirect_uri"

class BhzMagaluConfig(models.Model):
    _name = "bhz.magalu.config"
    _description = "Configuração Magalu (BHZ plug and play)"
    _rec_name = "name"

    name = fields.Char(default="Configuração Magalu", readonly=True)
    access_token = fields.Char("Access Token", readonly=True)
    refresh_token = fields.Char("Refresh Token", readonly=True)
    token_expires_at = fields.Datetime("Token expira em", readonly=True)
    environment = fields.Selection([
        ("production", "Produção"),
    ], default="production", required=True)

    client_id_display = fields.Char(
        string="Client ID (BHZ)",
        compute="_compute_client_params",
        readonly=True,
    )
    redirect_uri_display = fields.Char(
        string="Redirect URI",
        compute="_compute_client_params",
        readonly=True,
    )

    def _compute_client_params(self):
        ICP = self.env["ir.config_parameter"].sudo()
        client_id = ICP.get_param(CLIENT_ID_PARAM)
        redirect_uri = ICP.get_param(REDIRECT_PARAM)
        for rec in self:
            rec.client_id_display = client_id
            rec.redirect_uri_display = redirect_uri

    # grava tokens no próprio registro
    def write_tokens(self, token_data):
        expires_in = token_data.get("expires_in", 3600)
        expire_dt = fields.Datetime.now() + datetime.timedelta(seconds=expires_in - 60)
        self.write({
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_expires_at": expire_dt,
        })

    def action_get_authorization_url(self):
        """Redireciona o usuário para autorizar no Magalu usando o client fixo."""
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        client_id = ICP.get_param(CLIENT_ID_PARAM)
        redirect_uri = ICP.get_param(REDIRECT_PARAM)
        if not client_id or not redirect_uri:
            raise UserError(_("Client ID ou Redirect URI não estão configurados no sistema."))
        authorize_url = (
            "https://id.magalu.com/oauth/authorize"
            f"?response_type=code&client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=apiin:all"
        )
        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "self",
        }

    def action_refresh_token(self):
        self.ensure_one()
        self.env["bhz.magalu.api"].refresh_token(self)
