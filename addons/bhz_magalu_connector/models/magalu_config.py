import datetime
import logging
from urllib.parse import quote, urlencode

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MAGALU_AUTHORIZE_URL = "https://id.magalu.com/account/select"
MAGALU_SCOPES = [
    "open:portfolio-skus-seller:read",
    "open:portfolio-skus-seller:write",
    "open:portfolio-stocks-seller:read",
    "open:portfolio-stocks-seller:write",
    "open:order-order-seller:read",
    "open:order-delivery-seller:read",
    "open:order-invoice-seller:read",
    "open:ticket-messages-seller:read",
    "open:ticket-messages-seller:write",
    "open:ticket-events-seller:read",
    "open:ticket-events-seller:write",
    "open:tickets-seller:read",
    "open:trace:read",
    "open:queue-history:read",
    "services:questions-seller:read",
    "services:questions-seller:write",
    "services:conversations-seller:read",
    "services:conversations-seller:write",
]
MAGALU_SCOPE = " ".join(["openid"] + MAGALU_SCOPES)
CLIENT_ID_PARAM = "bhz_magalu.client_id"
CLIENT_SECRET_PARAM = "bhz_magalu.client_secret"
ALLOWED_REDIRECT_URIS = {
    "https://bhzsistemas.com.br/magalu/oauth/callback",
    "https://www.bhzsistemas.com.br/magalu/oauth/callback",
    "https://michelc16-bhz-sistemas-bhz-payment-25328227.dev.odoo.com/magalu/oauth/callback",
}


class BhzMagaluConfig(models.Model):
    _name = "bhz.magalu.config"
    _description = "Configuração Magalu (BHZ)"
    _rec_name = "name"
    _check_company_auto = True
    _order = "id desc"
    _sql_constraints = [
        ("unique_company", "unique(company_id)", "Cada empresa só pode ter uma configuração Magalu.")
    ]

    name = fields.Char(default="Configuração Magalu", readonly=True)
    environment = fields.Selection(
        [("production", "Produção")],
        string="Ambiente",
        default="production",
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    access_token = fields.Char("Access Token", readonly=True)
    refresh_token = fields.Char("Refresh Token", readonly=True)
    token_expires_at = fields.Datetime("Token expira em", readonly=True)

    # === Helpers ===
    def _get_system_param(self, key):
        return (self.env["ir.config_parameter"].sudo().get_param(key) or "").strip()

    def _get_client_credentials(self):
        client_id = self._get_system_param(CLIENT_ID_PARAM)
        client_secret = self._get_system_param(CLIENT_SECRET_PARAM)
        if not client_id or not client_secret:
            raise UserError("Client configurado incorretamente")
        return client_id, client_secret

    def _get_base_url(self):
        base_url = (self.env["ir.config_parameter"].sudo().get_param("web.base.url") or "").strip()
        if not base_url:
            raise UserError(_("Configure o parâmetro web.base.url antes de conectar ao Magalu."))
        return base_url.rstrip("/")

    def _get_redirect_uri(self):
        base_url = self._get_base_url()
        redirect_uri = f"{base_url}/magalu/oauth/callback"
        if redirect_uri not in ALLOWED_REDIRECT_URIS:
            raise UserError(
                _("Redirect URI calculada (%(found)s) não está entre as válidas: %(valid)s",
                  found=redirect_uri,
                  valid=", ".join(sorted(ALLOWED_REDIRECT_URIS)))
            )
        return redirect_uri

    def _build_state_param(self):
        if not self.id:
            raise UserError(_("Salve o registro antes de iniciar a conexão."))
        return f"cfg:{self.id}|url:{self._get_base_url()}"

    # === Tokens ===
    def write_tokens(self, token_data):
        expires_in = int(token_data.get("expires_in") or 0)
        expire_dt = fields.Datetime.now() + datetime.timedelta(seconds=max(expires_in - 30, 0))
        refresh_token = token_data.get("refresh_token") or self.refresh_token
        vals = {
            "access_token": token_data.get("access_token"),
            "token_expires_at": expire_dt,
        }
        if refresh_token:
            vals["refresh_token"] = refresh_token
        self.write(vals)

    # === Actions ===
    def action_connect_magalu(self):
        self.ensure_one()
        client_id, _ = self._get_client_credentials()
        redirect_uri = self._get_redirect_uri()
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": MAGALU_SCOPE,
            "choose_tenants": "true",
            "state": self._build_state_param(),
        }
        authorize_url = f"{MAGALU_AUTHORIZE_URL}?{urlencode(params, quote_via=quote, safe=':/')}"
        _logger.info("Magalu OAuth authorize URL (cfg %s): %s", self.id, authorize_url)
        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "new",
        }

    def action_refresh_token(self):
        self.ensure_one()
        self.env["bhz.magalu.api"].refresh_token(self)
        return True
