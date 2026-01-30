import datetime
import logging
import secrets
from urllib.parse import quote

import requests
from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

AUTH_URL = "https://auth.mercadolibre.com/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API_ME_URL = "https://api.mercadolibre.com/users/me"

PARAM_CLIENT_ID = "bhz_meli.client_id"
PARAM_CLIENT_SECRET = "bhz_meli.client_secret"
PARAM_REDIRECT_URI = "bhz_meli.redirect_uri"
TOKEN_LEEWAY_SECONDS = 60


class MeliAccount(models.Model):
    _name = "meli.account"
    _description = "Conta Mercado Livre (BHZ)"
    _check_company_auto = True

    name = fields.Char("Nome da conta", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company.id,
        required=True,
    )

    authorization_code = fields.Char("Authorization Code", readonly=True)
    auth_state_token = fields.Char("Token do state OAuth", readonly=True)
    access_token = fields.Char("Access Token", readonly=True)
    refresh_token = fields.Char("Refresh Token", readonly=True)
    token_expires_at = fields.Datetime("Token expira em", readonly=True)
    ml_user_id = fields.Char("ID Usuário ML", readonly=True)
    site_id = fields.Char("Site", readonly=True)

    last_sync_orders_at = fields.Datetime("Última sincronização de pedidos", readonly=True)
    last_sync_products_at = fields.Datetime("Última sincronização de produtos", readonly=True)
    last_error = fields.Text("Último erro", readonly=True)
    last_error_at = fields.Datetime("Data do último erro", readonly=True)

    state = fields.Selection(
        [
            ("draft", "Não conectado"),
            ("connected", "Conectado"),
            ("authorized", "Conectado (legado)"),
        ],
        default="draft",
        readonly=True,
    )

    # ---------------------------------------------------------------------
    # Helpers de configuração
    # ---------------------------------------------------------------------
    def _get_company(self):
        """Retorna a empresa respeitando multi-company."""
        self.ensure_one()
        return self.company_id or self.env.company

    def _get_credentials(self):
        """Lê client_id/secret/redirect_uri de ir.config_parameter para a empresa."""
        self.ensure_one()
        company = self._get_company()
        params = self.env["ir.config_parameter"].sudo().with_company(company)
        client_id = params.get_param(PARAM_CLIENT_ID)
        client_secret = params.get_param(PARAM_CLIENT_SECRET)
        redirect_uri = params.get_param(PARAM_REDIRECT_URI)

        missing = []
        if not client_id:
            missing.append("client_id")
        if not client_secret:
            missing.append("client_secret")
        if not redirect_uri:
            missing.append(f"redirect_uri ({PARAM_REDIRECT_URI})")
        if missing:
            raise UserError(
                _("Configuração do Mercado Livre ausente para %s: %s")
                % (company.display_name, ", ".join(missing))
            )

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }

    # ---------------------------------------------------------------------
    # Helpers de estado/erros
    # ---------------------------------------------------------------------
    def _record_error(self, message):
        now = fields.Datetime.now()
        self.sudo().write({"last_error": message, "last_error_at": now})

    def _clear_error(self):
        self.sudo().write({"last_error": False, "last_error_at": False})

    def _build_state_value(self):
        """Gera valor único de state (account_id:token) e salva o token."""
        token = secrets.token_urlsafe(24)
        self.sudo().write({"auth_state_token": token})
        return f"{self.id}:{token}"

    def _validate_state_value(self, state_value):
        """Valida se o state recebido pertence à conta."""
        self.ensure_one()
        if not state_value:
            raise UserError(_("State do OAuth não informado."))
        parts = state_value.split(":", 1)
        if len(parts) != 2:
            raise UserError(_("State inválido recebido do Mercado Livre."))
        account_id, token = parts
        if str(self.id) != account_id:
            raise UserError(_("State não corresponde a esta conta Mercado Livre."))
        if not self.auth_state_token or token != self.auth_state_token:
            raise UserError(_("State não reconhecido. Gere uma nova URL de autorização."))

    # ---------------------------------------------------------------------
    # Fluxo OAuth
    # ---------------------------------------------------------------------
    def action_get_authorize_url(self):
        """Monta a URL de autorização com state seguro."""
        self.ensure_one()
        if not self.id:
            raise UserError(_("Salve a conta antes de conectar ao Mercado Livre."))
        creds = self._get_credentials()
        state = self._build_state_value()

        params = {
            "response_type": "code",
            "client_id": creds["client_id"],
            "redirect_uri": creds["redirect_uri"],
            "state": state,
        }
        query = "&".join(f"{key}={quote(str(value))}" for key, value in params.items())
        url = f"{AUTH_URL}?{query}"
        _logger.info(
            "[ML][OAuth] URL gerada para a conta %s (empresa %s)",
            self.name,
            self.company_id.display_name,
        )
        self._clear_error()
        return url

    def action_open_authorize(self):
        """Ação do botão 'Conectar Mercado Livre'."""
        self.ensure_one()
        url = self.action_get_authorize_url()
        return {
            "type": "ir.actions.act_url",
            "name": "Conectar Mercado Livre",
            "target": "new",
            "url": url,
        }

    def _store_token_payload(self, payload, code=None):
        expires_in = int(payload.get("expires_in") or 0)
        expire_dt = fields.Datetime.now() + datetime.timedelta(
            seconds=max(expires_in - TOKEN_LEEWAY_SECONDS, 0)
        )
        vals = {
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token") or self.refresh_token,
            "token_expires_at": expire_dt,
        }
        if code:
            vals["authorization_code"] = code
        self.sudo().write(vals)

    def ensure_valid_token(self):
        """Garante que o token esteja válido antes de chamar a API."""
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Conta Mercado Livre sem access token. Conecte novamente."))
        if not self.token_expires_at or fields.Datetime.now() >= self.token_expires_at:
            _logger.info("[ML][OAuth] Token expirado para a conta %s. Renovando...", self.name)
            self.refresh_access_token()

    def _token_request(self, data, error_prefix):
        """Chamada centralizada para o endpoint de token com logs."""
        try:
            resp = requests.post(TOKEN_URL, data=data, timeout=30)
        except requests.RequestException as exc:
            _logger.exception("%s: erro na chamada HTTP: %s", error_prefix, exc)
            raise UserError(_("Falha de rede ao falar com o Mercado Livre."))

        if resp.status_code != 200:
            _logger.error("%s: %s - %s", error_prefix, resp.status_code, resp.text)
            raise UserError(_("Erro ao autenticar no Mercado Livre: %s") % resp.text)
        return resp.json()

    def exchange_code_for_token(self, code, state=None):
        """Troca o code que o ML devolve por access_token e salva na conta."""
        self.ensure_one()
        if state:
            self._validate_state_value(state)
        creds = self._get_credentials()
        data = {
            "grant_type": "authorization_code",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "code": code,
            "redirect_uri": creds["redirect_uri"],
        }

        _logger.info(
            "[ML][OAuth] Trocando code por token para a conta %s (empresa %s)",
            self.name,
            self.company_id.display_name,
        )
        payload = self._token_request(data, "[ML][OAuth] Erro ao trocar code por token")
        self._store_token_payload(payload, code=code)
        self.sudo().write({"state": "connected", "auth_state_token": False})
        self._clear_error()

        # pega dados do usuário do ML
        self._update_ml_identity()

    def _update_ml_identity(self):
        """Busca o ml_user_id/site_id usando o access_token atual."""
        self.ensure_one()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            resp = requests.get(API_ME_URL, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            _logger.warning("[ML][OAuth] Não foi possível ler /users/me: %s", exc)
            return

        info = resp.json()
        self.sudo().write(
            {
                "ml_user_id": info.get("id"),
                "site_id": info.get("site_id"),
            }
        )

    def refresh_access_token(self):
        """Renova o token quando expirar."""
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(_("Conta sem refresh token. Clique em Conectar novamente."))

        creds = self._get_credentials()
        data = {
            "grant_type": "refresh_token",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": self.refresh_token,
        }

        _logger.info("[ML][OAuth] Renovando token para a conta %s", self.name)
        payload = self._token_request(data, "[ML][OAuth] Erro ao renovar token")
        self._store_token_payload(payload)
        self._clear_error()
        return True
