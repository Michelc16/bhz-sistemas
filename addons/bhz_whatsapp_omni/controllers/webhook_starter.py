from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class BHZWAStarterInbound(http.Controller):

    @http.route('/bhz_wa/starter/inbound', type='json', auth='public', csrf=False)
    def inbound(self, **payload):
        """
        Payload esperado do serviço Starter (Node/Baileys):
        {
          "session_id": "default",
          "from": "5531999999999",
          "jid": "5531999999999@s.whatsapp.net",
          "body": "texto da mensagem",
          "ts": 1690000000,
          "signature": "opcional"
        }
        """
        try:
            env = request.env
            acc = env['bhz.wa.account'].sudo().search([('mode', '=', 'starter')], limit=1)
            if not acc:
                return {"ok": False, "error": "no_starter_account"}

            expected_secret = env['ir.config_parameter'].sudo().get_param('bhz_wa.starter_webhook_secret') or ''
            provided_secret = (
                request.httprequest.headers.get('X-BHZ-WA-Secret')
                or payload.get('secret')
            )
            if expected_secret and expected_secret != provided_secret:
                _logger.warning("Starter webhook secret inválido para payload %s", payload)
                return {"ok": False, "error": "invalid_secret"}

            session = env['bhz.wa.session'].sudo().search([
                ('session_id', '=', payload.get('session_id'))
            ], limit=1)
            if not session:
                base_url = acc._get_starter_base_url()
                session = env['bhz.wa.session'].sudo().create({
                    "name": f"Auto-{payload.get('session_id')}",
                    "session_id": payload.get('session_id') or "default",
                    "external_base_url": base_url,
                    "account_id": acc.id,
                })

            partner = request.env['res.partner'].sudo().search([
                ('phone', 'ilike', payload.get('from'))
            ], limit=1)

            msg = request.env['bhz.wa.message'].sudo().create({
                "account_id": acc.id,
                "session_id": session.id,
                "direction": "in",
                "partner_id": partner.id if partner else False,
                "remote_jid": payload.get('jid'),
                "remote_phone": payload.get('from'),
                "body": payload.get('body') or "",
                "state": "received",
                "provider": "starter",
            })

            if partner:
                partner.message_post(body=f"📲 WA Starter (IN): {msg.body}")

            acc.with_context(bypass_limits=True).try_ai_autoreply(msg)
            return {"ok": True}
        except Exception as e:
            _logger.exception("Starter inbound error: %s", e)
            return {"ok": False, "error": str(e)}
