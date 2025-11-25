import logging

import requests
from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MAGALU_TOKEN_URL = "https://id.magalu.com/oauth/token"
MAGALU_API_BASE = "https://developers-api.magalu.com/marketplace"
REQUEST_TIMEOUT = 30


class BhzMagaluAPI(models.AbstractModel):
    _name = "bhz.magalu.api"
    _description = "Cliente API Magalu (BHZ)"

    # ====== HTTP helpers ======
    def _do_request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        try:
            return requests.request(method, url, **kwargs)
        except requests.RequestException as exc:
            _logger.error("Erro de comunicação com a API Magalu: %s", exc)
            raise UserError(_("Erro de comunicação com a API Magalu: %s") % exc)

    def _format_response_error(self, resp):
        content = (resp.text or "").strip()
        if len(content) > 400:
            content = f"{content[:400]}..."
        return f"{resp.status_code} - {content or 'Sem corpo'}"

    # ====== REQUEST ======
    def _request(self, config_rec, method, endpoint, **kwargs):
        """Executa requisição autenticada à API do Magalu."""
        if not config_rec.access_token:
            raise UserError(_("Token Magalu não encontrado. Clique em Conectar Magalu."))

        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "Authorization": f"Bearer {config_rec.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        url = f"{MAGALU_API_BASE}{endpoint}"
        _logger.info("Magalu %s %s", method, url)

        resp = self._do_request(method, url, headers=headers, **kwargs)
        if resp.status_code == 401:
            _logger.warning("Token Magalu expirado. Tentando renovar automaticamente.")
            self.refresh_token(config_rec)
            headers["Authorization"] = f"Bearer {config_rec.access_token}"
            resp = self._do_request(method, url, headers=headers, **kwargs)

        if not resp.ok:
            error_msg = self._format_response_error(resp)
            _logger.error("Erro Magalu %s %s: %s", method, url, error_msg)
            raise UserError(_("Erro na API Magalu: %s") % error_msg)

        return resp.json() if resp.text else {}

    # ====== AUTH ======
    def _exchange_code_for_token(self, config_rec, code):
        """Troca o authorization code pelo access_token/refresh_token."""
        client_id, client_secret = config_rec._get_client_credentials()
        redirect_uri = config_rec._get_redirect_uri()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        token_data = self._post_token_payload(data, "authorization_code")
        config_rec.write_tokens(token_data)
        return token_data

    def exchange_code_for_token(self, config_rec, code):
        """Compat wrapper for legacy callers."""
        return self._exchange_code_for_token(config_rec, code)

    def refresh_token(self, config_rec):
        """Renova o access_token usando o refresh_token salvo."""
        if not config_rec.refresh_token:
            raise UserError(_("Sem refresh token salvo. Conecte novamente."))
        client_id, client_secret = config_rec._get_client_credentials()
        data = {
            "grant_type": "refresh_token",
            "refresh_token": config_rec.refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        _logger.info("Renovando token Magalu (cfg %s)...", config_rec.id)
        token_data = self._post_token_payload(data, "refresh_token")
        config_rec.write_tokens(token_data)
        _logger.info("Token Magalu renovado (cfg %s).", config_rec.id)
        return token_data

    def _post_token_payload(self, data, context):
        try:
            resp = requests.post(MAGALU_TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            _logger.error("Erro HTTP ao solicitar token (%s): %s", context, exc)
            raise UserError(_("Erro ao comunicar com o ID Magalu: %s") % exc)

        if resp.status_code != 200:
            error_msg = self._format_response_error(resp)
            _logger.error("ID Magalu respondeu erro (%s): %s", context, error_msg)
            raise UserError(_("ID Magalu retornou erro (%s): %s") % (context, error_msg))

        try:
            return resp.json()
        except ValueError:
            _logger.error("ID Magalu retornou payload não JSON (%s): %s", context, resp.text)
            raise UserError(_("Resposta inesperada do ID Magalu durante %s.") % context)

    # ====== PRODUTOS ======
    def push_stock(self, config_rec, sku, qty):
        """Atualiza estoque de um SKU."""
        payload = {"sku": sku, "available_quantity": qty}
        return self._request(config_rec, "POST", "/products/stock", json=payload)

    def push_product(self, config_rec, product_vals):
        """Cria ou atualiza produto."""
        return self._request(config_rec, "POST", "/products", json=product_vals)

    # ====== PEDIDOS ======
    def fetch_orders(self, config_rec):
        """Busca lista de pedidos."""
        return self._request(config_rec, "GET", "/orders")

    def fetch_order_detail(self, config_rec, order_id):
        """Busca detalhes de um pedido específico."""
        return self._request(config_rec, "GET", f"/orders/{order_id}")
