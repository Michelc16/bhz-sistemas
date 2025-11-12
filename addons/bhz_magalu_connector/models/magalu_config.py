import datetime
import logging
from urllib.parse import urlencode, quote

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MAGALU_AUTHORIZE_BASE = "https://id.magalu.com/login"
MAGALU_SCOPE = "openid apiin:all"
EXPECTED_REDIRECT_URI = "https://michelc16-bhz-sistemas-bhz-payment-25328227.dev.odoo.com/magalu/oauth/callback"
DEFAULT_CLIENT_ID = "dZCVzEyLat_rtRfHvNAuulhBUZBlz_6Lj_NZghlU7Qw"

CLIENT_ID_PARAM = "bhz_magalu.client_id"
REDIRECT_PARAM = "bhz_magalu.redirect_uri"


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

    def _default_client_id(self):
        return self.env["ir.config_parameter"].sudo().get_param(CLIENT_ID_PARAM) or DEFAULT_CLIENT_ID

    def _default_redirect_uri(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param(REDIRECT_PARAM)
            or EXPECTED_REDIRECT_URI
        )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    client_id = fields.Char(
        string="Client ID",
        required=True,
        default=_default_client_id,
        help="Identificador público fornecido pelo painel ID Magalu.",
    )
    client_secret = fields.Char(
        string="Client Secret",
        copy=False,
        help="Segredo do aplicativo no ID Magalu (nunca compartilhe).",
    )
    redirect_uri = fields.Char(
        string="Redirect URI",
        required=True,
        default=_default_redirect_uri,
        help=f"Precisa ser exatamente {EXPECTED_REDIRECT_URI}.",
    )

    access_token = fields.Char("Access Token", readonly=True)
    refresh_token = fields.Char("Refresh Token", readonly=True)
    token_expires_at = fields.Datetime("Token expira em", readonly=True)

    def write_tokens(self, token_data):
        expires_in = int(token_data.get("expires_in") or 0)
        expires_margin = max(expires_in - 30, 0)
        expire_dt = fields.Datetime.now() + datetime.timedelta(seconds=expires_margin)
        refresh_token = token_data.get("refresh_token") or self.refresh_token
        vals = {
            "access_token": token_data.get("access_token"),
            "token_expires_at": expire_dt,
        }
        if refresh_token:
            vals["refresh_token"] = refresh_token
        self.write(vals)

    # === AUTH FLOW ===
    def _get_base_url(self):
        return self.env["ir.config_parameter"].sudo().get_param("web.base.url")

    def _build_state_param(self):
        base_url = self._get_base_url()
        if not base_url:
            raise UserError(_("Parâmetro 'web.base.url' não foi configurado."))
        return f"cfg:{self.id}|url:{base_url}"

    def _build_authorize_url(self):
        self.ensure_one()
        client_id = (self.client_id or "").strip()
        redirect_uri = (self.redirect_uri or "").strip()

        if not client_id:
            raise UserError(_("Configure o Client ID antes de conectar ao Magalu."))
        if redirect_uri != EXPECTED_REDIRECT_URI:
            raise UserError(
                _(
                    "A Redirect URI precisa ser exatamente %(uri)s. Ajuste o campo antes de continuar.",
                    uri=EXPECTED_REDIRECT_URI,
                )
            )

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": MAGALU_SCOPE,
            "choose_tenants": "true",
            "state": self._build_state_param(),
        }
        url = f"{MAGALU_AUTHORIZE_BASE}?{urlencode(params, quote_via=quote, safe='')}"
        _logger.debug("Magalu authorize URL (config %s): %s", self.id, url)
        return url

    def action_get_authorization_url(self):
        self.ensure_one()
        authorize_url = self._build_authorize_url()
        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "new",
        }

    def action_refresh_token(self):
        self.ensure_one()
        api = self.env["bhz.magalu.api"]
        api.refresh_token(self)
        return True
