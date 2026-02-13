import base64
import datetime
import hmac
import json
import logging
import os
from hashlib import sha256
from urllib.parse import quote

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MAGALU_AUTHORIZE_URL = "https://id.magalu.com/login"
CLIENT_ID_PARAM = "bhz_magalu.client_id"
CLIENT_SECRET_PARAM = "bhz_magalu.client_secret"
REQUESTED_SCOPES_PARAM = "bhz_magalu.oauth_scopes"
ALLOWED_SCOPES_PARAM = "bhz_magalu.allowed_scopes"
STATE_SECRET_PARAM = "bhz_magalu.state_secret"
SCOPE_MODE_PARAM = "bhz_magalu.scope_mode"
DEFAULT_SCOPES = [
    "open:portfolio:read",
    "open:order-order:read",
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
    _unique_company = models.Constraint(
        'UNIQUE(company_id)',
        'Cada empresa só pode ter uma configuração Magalu.',
    )

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
    oauth_state_nonce = fields.Char(string="Nonce OAuth", readonly=True, copy=False)
    oauth_state_expiration = fields.Datetime(string="Expiração do nonce", readonly=True, copy=False)

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
        nonce = os.urandom(16).hex()
        payload = {
            "db": self.env.cr.dbname,
            "company_id": self.company_id.id,
            "config_id": self.id,
            "return_url": self._get_base_url(),
            "nonce": nonce,
            "ts": int(datetime.datetime.utcnow().timestamp()),
        }
        payload_json = json.dumps(payload, separators=(",", ":"))
        payload["sig"] = self._compute_state_signature(payload_json)
        state_raw = json.dumps(payload, separators=(",", ":")).encode()
        state = base64.urlsafe_b64encode(state_raw).decode().rstrip("=")
        self.write(
            {
                "oauth_state_nonce": nonce,
                "oauth_state_expiration": fields.Datetime.now() + datetime.timedelta(minutes=10),
            }
        )
        return state

    def _parse_scopes(self, scope_string):
        return [token.strip() for token in scope_string.split() if token.strip()]

    def _get_requested_scopes(self):
        mode = (self._get_system_param(SCOPE_MODE_PARAM) or "production").lower().strip()
        if mode == "test":
            scope_string = "open:portfolio:read"
            _logger.info(
                "Magalu OAuth scopes (%s): modo teste ativado, usando escopo %s",
                self.display_name,
                scope_string,
            )
            return scope_string
        requested_raw = self._get_system_param(REQUESTED_SCOPES_PARAM)
        requested = self._parse_scopes(requested_raw) if requested_raw else list(DEFAULT_SCOPES)
        if not requested:
            raise UserError(
                _(
                    "Nenhum scope configurado. Ajuste o parâmetro %(param)s com os scopes aprovados para o client.",
                    param=REQUESTED_SCOPES_PARAM,
                )
            )

        allowed_raw = self._get_system_param(ALLOWED_SCOPES_PARAM)
        final_scopes = []
        if allowed_raw:
            allowed = set(self._parse_scopes(allowed_raw))
            if not allowed:
                raise UserError(
                    _(
                        "O parâmetro %(param)s está vazio. Preencha com a lista de scopes habilitados pelo client ou remova o parâmetro.",
                        param=ALLOWED_SCOPES_PARAM,
                    )
                )
            for scope in requested:
                if scope in allowed and scope.startswith("open:"):
                    final_scopes.append(scope)
        else:
            for scope in requested:
                if scope.startswith("open:"):
                    final_scopes.append(scope)

        dedup_scopes = []
        for scope in final_scopes:
            if scope not in dedup_scopes:
                dedup_scopes.append(scope)

        if not dedup_scopes:
            raise UserError(
                _(
                    "Nenhum scope válido configurado para este client. Ajuste %(param)s ou atualize o client no ID Magalu.",
                    param=REQUESTED_SCOPES_PARAM,
                )
            )

        scope_string = " ".join(dedup_scopes)
        _logger.info("Magalu OAuth scopes (%s): %s", self.display_name, scope_string)
        return scope_string

    def _get_state_secret(self):
        secret = self._get_system_param(STATE_SECRET_PARAM)
        if not secret:
            secret = os.urandom(32).hex()
            self.env["ir.config_parameter"].sudo().set_param(STATE_SECRET_PARAM, secret)
        return secret

    def _compute_state_signature(self, base_string):
        secret = self._get_state_secret()
        return hmac.new(secret.encode(), base_string.encode(), sha256).hexdigest()

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
        state = self._build_state_param()
        scope_param = quote(scope, safe=":")
        query_parts = [
            f"client_id={quote(client_id)}",
            f"redirect_uri={quote(redirect_uri, safe=':/')}",
            f"scope={scope_param}",
            "response_type=code",
            "choose_tenants=true",
            f"state={state}",
        ]
        authorize_url = f"{MAGALU_AUTHORIZE_URL}?{'&'.join(query_parts)}"
        _logger.info(
            "Magalu OAuth authorize URL (%s): endpoint=%s scopes=%s state=%s mode=%s",
            self.display_name,
            MAGALU_AUTHORIZE_URL,
            scope,
            state[-8:],
            self._get_system_param(SCOPE_MODE_PARAM) or "production",
        )
        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "new",
        }

    def action_refresh_token(self):
        self.ensure_one()
        self.env["bhz.magalu.api"].refresh_token(self)
        return True

    def _validate_state(self, state_payload):
        base_url = self._get_base_url()
        if int(state_payload.get("config_id") or 0) != self.id:
            raise UserError(_("State não corresponde a esta configuração."))
        if state_payload.get("return_url") != base_url:
            raise UserError(_("State não corresponde a esta instância."))

        sig = state_payload.get("sig")
        payload_copy = state_payload.copy()
        payload_copy.pop("sig", None)
        payload_json = json.dumps(payload_copy, separators=(",", ":"))
        expected_sig = self._compute_state_signature(payload_json)
        if sig != expected_sig:
            raise UserError(_("State inválido (assinatura incorreta)."))

        nonce = state_payload.get("nonce")
        if not nonce or not self.oauth_state_nonce or nonce != self.oauth_state_nonce:
            raise UserError(_("State nonce não corresponde ao último pedido de autorização."))
        if not self.oauth_state_expiration or fields.Datetime.now() > self.oauth_state_expiration:
            raise UserError(_("O link de autorização expirou. Tente conectar novamente."))

        self.write({"oauth_state_nonce": False, "oauth_state_expiration": False})
