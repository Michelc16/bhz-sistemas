import datetime
import logging
from urllib.parse import quote, urlencode

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MAGALU_AUTHORIZE_URL = "https://id.magalu.com/login"
CLIENT_ID_PARAM = "bhz_magalu.client_id"
CLIENT_SECRET_PARAM = "bhz_magalu.client_secret"
REQUESTED_SCOPES_PARAM = "bhz_magalu.requested_scopes"
ALLOWED_SCOPES_PARAM = "bhz_magalu.allowed_scopes"
DEFAULT_SCOPES = [
    "open:order-order-seller:read",
    "open:order-delivery-seller:read",
    "open:order-invoice-seller:read",
    "open:portfolio-skus-seller:read",
    "open:portfolio-stocks-seller:read",
]
ALLOWED_REDIRECT_URIS = {
    "https://bhzsistemas.com.br/magalu/oauth/callback",
    "https://www.bhzsistemas.com.br/magalu/oauth/callback",
    "https://michelc16-bhz-sistemas-bhz-payment-25328227.dev.odoo.com/magalu/oauth/callback",
    "https://michelc16-bhz-sistemas-bhz-stock-25931562.dev.odoo.com/magalu/oauth/callback",
    "https://michelc16-bhz-sistemas-bhz-rma-25937183.dev.odoo.com/magalu/oauth/callback",
}


class BhzMagaluConfig(models.Model):
    _name = "bhz.magalu.config"
    _description = "Configuração Magalu (BHZ)"
    _rec_name = "name"
    _check_company_auto = True
    _order = "id desc"
    _sql_constraints = [
        ("unique_company", "unique(company_id)", "Cada empresa só pode ter uma configuração Magalu."),
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
                _(
                    "Redirect URI calculada (%(found)s) não está entre as válidas: %(valid)s",
                    found=redirect_uri,
                    valid=", ".join(sorted(ALLOWED_REDIRECT_URIS)),
                )
            )
        return redirect_uri

    def _build_state_param(self):
        if not self.id:
            raise UserError(_("Salve o registro antes de iniciar a conexão."))
        return f"cfg:{self.id}|url:{self._get_base_url()}"

    def _parse_scopes(self, scope_string):
        return [token.strip() for token in scope_string.split() if token.strip()]

    def _get_requested_scopes(self):
        requested_raw = self._get_system_param(REQUESTED_SCOPES_PARAM)
        requested = self._parse_scopes(requested_raw) if requested_raw else list(DEFAULT_SCOPES)

        allowed_raw = self._get_system_param(ALLOWED_SCOPES_PARAM)
        if allowed_raw:
            allowed = set(self._parse_scopes(allowed_raw))
            final_scopes = [scope for scope in requested if scope in allowed]
        else:
            final_scopes = []
            for scope in requested:
                if scope == "apiin:all":
                    final_scopes.append(scope)
                elif scope.startswith("open:") or scope.startswith("services:"):
                    final_scopes.append(scope)

        # remove duplicados preservando ordem
        dedup_scopes = []
        for scope in final_scopes:
            if scope not in dedup_scopes:
                dedup_scopes.append(scope)

        if not dedup_scopes:
            raise UserError(
                _(
                    "Nenhum scope válido configurado para este client. Ajuste o parâmetro %(param)s ou solicite ao suporte Magalu a liberação dos scopes necessários.",
                    param=REQUESTED_SCOPES_PARAM,
                )
            )

        scope_string = " ".join(dedup_scopes)
        _logger.info("Magalu OAuth scopes (%s): %s", self.display_name, scope_string)
        return scope_string

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
        scope = self._get_requested_scopes()
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scope,
            "choose_tenants": "true",
            "state": self._build_state_param(),
        }
        authorize_url = f"{MAGALU_AUTHORIZE_URL}?{urlencode(params, quote_via=quote, safe=':/')}"
        _logger.info("Magalu OAuth authorize URL (%s): %s", self.display_name, authorize_url)
        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "new",
        }

    def action_refresh_token(self):
        self.ensure_one()
        self.env["bhz.magalu.api"].refresh_token(self)
        return True
