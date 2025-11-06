import logging
import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MAGALU_TOKEN_URL = "https://id.magalu.com/oauth/token"
MAGALU_API_BASE = "https://developers-api.magalu.com/marketplace"

CLIENT_ID_PARAM = "bhz_magalu.client_id"
CLIENT_SECRET_PARAM = "bhz_magalu.client_secret"
REDIRECT_PARAM = "bhz_magalu.redirect_uri"


class BhzMagaluAPI(models.AbstractModel):
    _name = "bhz.magalu.api"
    _description = "Cliente API Magalu (BHZ)"

    def _get_fixed_credentials(self):
        ICP = self.env["ir.config_parameter"].sudo()
        client_id = ICP.get_param(CLIENT_ID_PARAM)
        client_secret = ICP.get_param(CLIENT_SECRET_PARAM)
        redirect_uri = ICP.get_param(REDIRECT_PARAM)
        if not client_id or not client_secret or not redirect_uri:
            raise UserError(_("Parâmetros Magalu não configurados. Verifique o data/magalu_params.xml."))
        return client_id, client_secret, redirect_uri

    def _request(self, config_rec, method, endpoint, **kwargs):
        if not config_rec.access_token:
            raise UserError(_("Token Magalu não encontrado. Clique em Conectar Magalu."))
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"Bearer {config_rec.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        url = f"{MAGALU_API_BASE}{endpoint}"
        _logger.info("Magalu %s %s", method, url)
        resp = requests.request(method, url, headers=headers, **kwargs)
        if resp.status_code == 401:
            # expirada: tenta renovar
            self.refresh_token(config_rec)
            headers["Authorization"] = f"Bearer {config_rec.access_token}"
            resp = requests.request(method, url, headers=headers, **kwargs)
        if not resp.ok:
            _logger.error("Erro Magalu %s: %s", resp.status_code, resp.text)
            raise UserError(_("Erro na API Magalu: %s") % resp.text)
        return resp.json() if resp.text else {}

    # ===== AUTH =====
    def exchange_code_for_token(self, config_rec, code):
        client_id, client_secret, redirect_uri = self._get_fixed_credentials()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        resp = requests.post(MAGALU_TOKEN_URL, data=data)
        if not resp.ok:
            raise UserError(_("Falha ao trocar code por token: %s") % resp.text)
        token_data = resp.json()
        config_rec.write_tokens(token_data)
        return token_data

    def refresh_token(self, config_rec):
        client_id, client_secret, _ = self._get_fixed_credentials()
        if not config_rec.refresh_token:
            raise UserError(_("Sem refresh token salvo. Conecte novamente."))
        data = {
            "grant_type": "refresh_token",
            "refresh_token": config_rec.refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        resp = requests.post(MAGALU_TOKEN_URL, data=data)
        if not resp.ok:
            raise UserError(_("Falha ao renovar token: %s") % resp.text)
        config_rec.write_tokens(resp.json())

    # ===== PRODUTOS =====
    def push_stock(self, config_rec, sku, qty):
        payload = {
            "sku": sku,
            "available_quantity": qty,
        }
        return self._request(config_rec, "POST", "/products/stock", json=payload)

    def push_product(self, config_rec, product_vals):
        return self._request(config_rec, "POST", "/products", json=product_vals)

    # ===== PEDIDOS =====
    def fetch_orders(self, config_rec):
        return self._request(config_rec, "GET", "/orders")

    def fetch_order_detail(self, config_rec, order_id):
        return self._request(config_rec, "GET", f"/orders/{order_id}")
