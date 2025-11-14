from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class BHZWAStarterInbound(http.Controller):

    @http.route('/bhz_wa/starter/inbound', type='json', auth='public', csrf=False)
    def inbound(self, **payload):
        """
        Espera: { session_id, from, jid, body, ts, signature? }
        """
        try:
            acc = request.env['bhz.wa.account'].sudo().search([('mode', '=', 'starter')], limit=1)
            if not acc:
                return {"ok": False, "error": "no_starter_account"}

            # TODO: validar assinatura HMAC se usar webhook_secret

            session = request.env['bhz.wa.session'].sudo().search([
                ('session_id', '=', payload.get('session_id'))
            ], limit=1)
            if not session:
                session = request.env['bhz.wa.session'].sudo().create({
                    "name": f"Auto-{payload.get('session_id')}",
                    "session_id": payload.get('session_id'),
                    "external_base_url": acc.starter_base_url,
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
