# -*- coding: utf-8 -*-
import logging
import time
import requests
from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class BhzIFoodClient(models.AbstractModel):
    _name = "bhz.ifood.client"
    _description = "HTTP Client iFood"

    def _account(self):
        acc_id = self.env.context.get("ifood_account_id")
        if not acc_id:
            raise UserError("Contexto sem ifood_account_id.")
        return self.env["bhz.ifood.account"].browse(acc_id).sudo()

    def _headers(self, token: str | None):
        h = {"Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def ensure_token(self):
        """Garante que existe token válido. Regra: renovar só quando necessário (boas práticas)."""
        acc = self._account()
        if acc.access_token and acc.token_expires_at and acc.token_expires_at.timestamp() > time.time() + 60:
            return acc.access_token

        # OAuth2: obter token — detalhes exatos dependem do fluxo do portal
        # iFood: OAuth2 Bearer. :contentReference[oaicite:4]{index=4}
        # Aqui deixamos um “token endpoint” configurável por você.
        token_url = f"{acc._get_base_url()}/authentication/v1.0/oauth/token"
        if not acc.client_id or not acc.client_secret:
            raise UserError("Client ID/Secret não configurados na conta iFood.")

        payload = {
            "grantType": "client_credentials",
            "clientId": acc.client_id,
            "clientSecret": acc.client_secret,
        }

        try:
            r = requests.post(token_url, json=payload, timeout=30)
            if r.status_code >= 400:
                acc.last_error = f"Token error {r.status_code}: {r.text}"
                _logger.error("iFood token error: %s %s", r.status_code, r.text)
                raise UserError("Falha ao obter token iFood. Veja o log/erro na conta.")
            data = r.json()
        except Exception as e:
            acc.last_error = str(e)
            raise

        acc.access_token = data.get("accessToken") or data.get("access_token")
        acc.refresh_token = data.get("refreshToken") or data.get("refresh_token")
        expires_in = int(data.get("expiresIn") or data.get("expires_in") or 3600)

        acc.token_expires_at = self.env.cr.now() + self.env["ir.fields.converter"].to_timedelta(expires_in)
        acc.last_error = False
        return acc.access_token

    def ping(self):
        """Ping genérico: substitua por endpoint real do seu módulo/categoria."""
        acc = self._account()
        token = self.ensure_token()
        url = f"{acc._get_base_url()}/health"
        try:
            r = requests.get(url, headers=self._headers(token), timeout=15)
            return r.status_code < 400
        except Exception:
            return False

    # --- Pedidos (polling) ---
    def fetch_orders_since(self, since_iso: str):
        """Busque pedidos por janela. Substitua pelos endpoints corretos da Order API."""
        acc = self._account()
        token = self.ensure_token()

        # Exemplo: endpoint varia. Há guia de Order API no portal Merchant. :contentReference[oaicite:5]{index=5}
        url = f"{acc._get_base_url()}/order/v1.0/orders?since={since_iso}"
        r = requests.get(url, headers=self._headers(token), timeout=60)
        if r.status_code >= 400:
            raise UserError(f"Erro ao buscar pedidos iFood: {r.status_code} {r.text}")
        return r.json()
