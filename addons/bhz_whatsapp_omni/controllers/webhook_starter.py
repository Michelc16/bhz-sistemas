import json
from datetime import datetime
from odoo import fields, http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class BHZWAStarterInbound(http.Controller):

    @http.route('/bhz_wa/starter/inbound', type='json', auth='public', csrf=False, methods=['POST'])
    def inbound(self, **payload):
        payload = payload or request.jsonrequest or {}
        try:
            env = request.env.sudo()
            expected_secret = env['ir.config_parameter'].get_param('starter_service.secret') or ''
            provided_secret = request.httprequest.headers.get('X-Webhook-Secret') or payload.get('secret')
            if expected_secret and provided_secret != expected_secret:
                _logger.warning("Starter webhook secret inválido.")
                return {"status": "error", "message": "invalid_secret"}

            session_code = payload.get('session') or payload.get('session_id')
            Account = env['bhz.wa.account']
            account = False
            if session_code:
                account = Account.search([('starter_session_id', '=', session_code)], limit=1)
            if not account:
                account = Account.search([('mode', '=', 'starter')], limit=1)
            if not account:
                return {"status": "error", "message": "no_account"}

            Session = env['bhz.wa.session']
            session = False
            if session_code:
                session = Session.search([('session_id', '=', session_code)], limit=1)
            if not session and session_code:
                session = Session.create({
                    "name": f"Sessão {session_code}",
                    "session_id": session_code,
                    "external_base_url": account._get_starter_base_url(),
                    "account_id": account.id,
                })

            from_number = payload.get('from') or ''
            remote_jid = payload.get('raw', {}).get('key', {}).get('remoteJid') if isinstance(payload.get('raw'), dict) else False
            remote_jid = remote_jid or (from_number if '@' in from_number else f"{from_number}@s.whatsapp.net")
            text = payload.get('message') or payload.get('body') or ''

            partner = env['res.partner'].search([
                '|',
                ('phone', 'ilike', from_number),
                ('mobile', 'ilike', from_number),
            ], limit=1)

            timestamp = payload.get('timestamp') or payload.get('ts')
            wa_dt = fields.Datetime.now()
            if timestamp:
                try:
                    wa_dt = fields.Datetime.to_string(datetime.utcfromtimestamp(float(timestamp)))
                except Exception:
                    wa_dt = fields.Datetime.now()

            msg = env['bhz.wa.message'].create({
                "account_id": account.id,
                "session_id": session.id if session else False,
                "direction": "in",
                "partner_id": partner.id if partner else False,
                "remote_jid": remote_jid,
                "remote_phone": from_number,
                "wa_from": from_number,
                "wa_to": account.starter_session_id,
                "body": text,
                "state": "new",
                "provider": "starter",
                "wa_timestamp": wa_dt,
                "payload_json": json.dumps(payload),
            })

            account.write({
                'starter_status': 'connected',
                'starter_last_number': from_number,
            })

            if partner:
                partner.message_post(body=f"📲 WA Starter (IN): {msg.body}")

            account.with_context(bypass_limits=True).try_ai_autoreply(msg)
            return {"status": "ok"}
        except Exception as e:
            _logger.exception("Starter inbound error: %s", e)
            return {"status": "error", "message": str(e)}
