# -*- coding: utf-8 -*-
import hmac
import hashlib
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class BhzIFoodWebhookController(http.Controller):

    @http.route("/ifood/webhook/<string:account_token>", type="json", auth="public", methods=["POST"], csrf=False)
    def ifood_webhook(self, account_token, **kwargs):
        """
        Endpoint para receber eventos.
        iFood manda assinatura em X-IFood-Signature (valide conforme docs). :contentReference[oaicite:8]{index=8}
        """
        acc = request.env["bhz.ifood.account"].sudo().search([("webhook_secret", "=", account_token)], limit=1)
        if not acc or not acc.webhook_enabled:
            return {"ok": False, "error": "account_not_found"}

        body = request.httprequest.data or b""
        signature = request.httprequest.headers.get("X-IFood-Signature")  # :contentReference[oaicite:9]{index=9}

        if signature and acc.webhook_secret:
            expected = hmac.new(
                acc.webhook_secret.encode("utf-8"),
                body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                _logger.warning("iFood webhook invalid signature for account %s", acc.id)
                return {"ok": False, "error": "invalid_signature"}

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        # MVP: se vier um evento de pedido, criar/atualizar bhz.ifood.order
        # Estrutura do payload varia (order events / presence events). :contentReference[oaicite:10]{index=10}
        order_id = payload.get("orderId") or payload.get("order_id")
        status = payload.get("status")

        if order_id:
            Order = request.env["bhz.ifood.order"].sudo()
            rec = Order.search([("ifood_order_id", "=", order_id), ("company_id", "=", acc.company_id.id)], limit=1)
            vals = {
                "company_id": acc.company_id.id,
                "account_id": acc.id,
                "ifood_order_id": order_id,
                "status": status,
                "raw_payload": body.decode("utf-8"),
            }
            if rec:
                rec.write(vals)
            else:
                Order.create(vals)

        return {"ok": True}
