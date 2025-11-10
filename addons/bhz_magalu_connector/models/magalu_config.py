from odoo import models, fields, _
from odoo.exceptions import UserError
from urllib.parse import quote
import datetime

CLIENT_ID_PARAM = "bhz_magalu.client_id"
CLIENT_SECRET_PARAM = "bhz_magalu.client_secret"
REDIRECT_PARAM = "bhz_magalu.redirect_uri"


class BhzMagaluConfig(models.Model):
    _name = "bhz.magalu.config"
    _description = "Configuração Magalu (BHZ)"
    _rec_name = "name"
    _order = "id desc"

    name = fields.Char(default="Configuração Magalu", readonly=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    access_token = fields.Char(readonly=True)
    refresh_token = fields.Char(readonly=True)
    token_expires_at = fields.Datetime(readonly=True)

    def write_tokens(self, token_data):
        expires_in = token_data.get("expires_in", 3600)
        expire_dt = fields.Datetime.now() + datetime.timedelta(seconds=expires_in - 60)
        self.write({
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_expires_at": expire_dt,
        })

    def action_get_authorization_url(self):
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        client_id = ICP.get_param(CLIENT_ID_PARAM)
        redirect_uri = ICP.get_param(REDIRECT_PARAM)

        if not client_id or not redirect_uri:
            raise UserError("Parâmetros BHZ Magalu não configurados (client_id/redirect).")

        redirect_encoded = quote(redirect_uri, safe="")
        
        scopes_raw = " ".join([
            "openid",
            "apiin:all",
            "open:order-order-seller:read",
            "open:order-delivery-seller:read",
            "open:order-invoice-seller:read",
            "open:portfolio-skus-seller:read",
            "open:portfolio-stocks-seller:read",
            "open:portfolio-stocks-seller:write",
        ])
        scopes_encoded = quote(scopes_raw, safe="")

        audience_raw = "https://api.magalu.com https://services.magalu.com"
        audience_encoded = quote(audience_raw, safe="")

        base_url = ICP.get_param("web.base.url") or self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        state_raw = f"cfg:{self.id}|url:{base_url}"
        state_encoded = quote(state_raw, safe="")      

        authorize_url = (
            "https://id.magalu.com/login"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_encoded}"
            f"&scope={scopes_encoded}"
            f"&response_type=code"
            f"&audience={audience_encoded}"
            f"&choose_tenants=true"
            f"&state={state_encoded}"
        )

        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "self",
        }
