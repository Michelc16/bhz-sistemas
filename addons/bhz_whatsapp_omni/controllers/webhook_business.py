from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class BHZWABusinessWebhook(http.Controller):

    @http.route('/bhz_wa/business/webhook', type='http', auth='public', csrf=False, methods=['GET'])
    def verify(self, **params):
        """
        Verificação de webhook (GET) da Meta:
        /bhz_wa/business/webhook?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
        """
        acc = request.env['bhz.wa.account'].sudo().search([('mode', '=', 'business')], limit=1)
        token = acc and acc.business_verify_token or ''
        if params.get('hub.mode') == 'subscribe' and params.get('hub.verify_token') == token:
            return params.get('hub.challenge', '')
        return "forbidden"

    @http.route('/bhz_wa/business/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def inbound(self, **payload):
        """
        Webhook de mensagens da Cloud API.
        """
        try:
            acc = request.env['bhz.wa.account'].sudo().search([('mode', '=', 'business')], limit=1)
            if not acc:
                return {"ok": False, "error": "no_business_account"}

            changes = payload.get('entry', [{}])[0].get('changes', [])
            for ch in changes:
                value = ch.get('value', {})
                msgs = value.get('messages', [])
                for m in msgs:
                    from_phone = m.get('from')  # 5531...
                    if m.get('type') == 'text':
                        body = m.get('text', {}).get('body')
                    else:
                        body = '[mensagem não-texto]'
                    jid = f"{from_phone}@s.whatsapp.net"

                    partner = request.env['res.partner'].sudo().search([
                        ('phone', 'ilike', from_phone)
                    ], limit=1)

                    msg = request.env['bhz.wa.message'].sudo().create({
                        "account_id": acc.id,
                        "direction": "in",
                        "partner_id": partner.id if partner else False,
                        "remote_jid": jid,
                        "remote_phone": from_phone,
                        "body": body or "",
                        "state": "received",
                        "provider": "business",
                    })

                    if partner:
                        partner.message_post(body=f"📲 WA Business (IN): {msg.body}")

                    acc.with_context(bypass_limits=True).try_ai_autoreply(msg)

            return {"ok": True}
        except Exception as e:
            _logger.exception("Business inbound error: %s", e)
            return {"ok": False, "error": str(e)}
