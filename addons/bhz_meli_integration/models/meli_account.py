import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ================== CONFIGURAÇÃO FIXA BHZ ==================
# ID que apareceu na sua tela: 3010146478781244
MELI_CLIENT_ID = "3010146478781244"

# Trocar pelo secret real da sua aplicação Mercado Livre
MELI_CLIENT_SECRET = "nRamhrvhMZvrgS5XB4DQ2tr04oXz7Wrg"

# Mesma URL que você cadastrou no Mercado Livre Developers
REDIRECT_URI = "https://www.bhzsistemas.com.br/meli/auth/callback"
# ===========================================================

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API_ME_URL = "https://api.mercadolibre.com/users/me"


class MeliAccount(models.Model):
    _name = "meli.account"
    _description = "Conta Mercado Livre (BHZ)"

    name = fields.Char("Nome da conta", required=True)
    company_id = fields.Many2one("res.company", string="Empresa", default=lambda self: self.env.company.id)

    # ficam travados porque o ERP que fornece
    client_id = fields.Char("Client ID", default=MELI_CLIENT_ID, readonly=True)
    client_secret = fields.Char("Client Secret", default=MELI_CLIENT_SECRET, readonly=True)
    redirect_uri = fields.Char("Redirect URI", default=REDIRECT_URI, readonly=True)

    authorization_code = fields.Char("Authorization Code", readonly=True)
    access_token = fields.Char("Access Token", readonly=True)
    refresh_token = fields.Char("Refresh Token", readonly=True)
    token_expires_in = fields.Datetime("Token expira em", readonly=True)
    ml_user_id = fields.Char("ID Usuário ML", readonly=True)
    site_id = fields.Char("Site", readonly=True)

    state = fields.Selection([
        ("draft", "Não conectado"),
        ("authorized", "Conectado"),
    ], default="draft", readonly=True)

    def action_get_authorize_url(self):
        """Monta a URL de autorização com state=<id da conta>."""
        self.ensure_one()
        base = "https://auth.mercadolibre.com/authorization"
        params = (
            f"?response_type=code"
            f"&client_id={MELI_CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&state={self.id}"
        )
        return base + params

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

    def exchange_code_for_token(self, code):
        """Troca o code que o ML devolve por access_token e salva na conta."""
        self.ensure_one()
        data = {
            "grant_type": "authorization_code",
            "client_id": MELI_CLIENT_ID,
            "client_secret": MELI_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        resp = requests.post(TOKEN_URL, data=data, timeout=30)
        if resp.status_code != 200:
            _logger.error("Erro ao trocar code por token ML: %s", resp.text)
            raise UserError(_("Erro ao autenticar no Mercado Livre: %s") % resp.text)

        payload = resp.json()
        self.write({
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token"),
            "authorization_code": code,
            "state": "authorized",
        })

        # pega dados do usuário do ML
        headers = {"Authorization": f"Bearer {self.access_token}"}
        me = requests.get(API_ME_URL, headers=headers, timeout=30)
        if me.status_code == 200:
            info = me.json()
            self.ml_user_id = info.get("id")
            self.site_id = info.get("site_id")

    def refresh_access_token(self):
        """Renova o token quando expirar."""
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(_("Conta sem refresh token. Clique em Conectar novamente."))
        data = {
            "grant_type": "refresh_token",
            "client_id": MELI_CLIENT_ID,
            "client_secret": MELI_CLIENT_SECRET,
            "refresh_token": self.refresh_token,
        }
        resp = requests.post(TOKEN_URL, data=data, timeout=30)
        if resp.status_code != 200:
            _logger.error("Erro ao renovar token ML: %s", resp.text)
            raise UserError(_("Erro ao renovar token do Mercado Livre: %s") % resp.text)

        payload = resp.json()
        self.write({
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token") or self.refresh_token,
        })
        return True
