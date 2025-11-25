import json
from datetime import datetime
from odoo import fields, http
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
        mode = params.get('hub.mode')
        verify_token = params.get('hub.verify_token')
        challenge = params.get('hub.challenge', '')

        if mode != 'subscribe':
            return "forbidden"

        env = request.env.sudo()
        Account = env['bhz.wa.account']
        token_ok = Account.search_count([('business_verify_token', '=', verify_token)]) > 0
        if not token_ok:
            global_token = env['ir.config_parameter'].get_param('bhz_wa.business_verify_token') or ''
            token_ok = bool(global_token and global_token == verify_token)

        if token_ok:
            return challenge
        return "forbidden"

    @http.route('/bhz_wa/business/webhook', type='json', auth='public', csrf=False, methods=['POST'])
    def inbound(self, **payload):
        """
        Webhook de mensagens da Cloud API.
        """
        payload = payload or request.jsonrequest or {}
        try:
            env = request.env.sudo()
            Account = env['bhz.wa.account']
            entries = payload.get('entry', []) or []
            for entry in entries:
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    metadata = value.get('metadata', {})
                    phone_id = metadata.get('phone_number_id')
                    if not phone_id:
                        continue
                    account = Account.search([('business_phone_number_id', '=', phone_id)], limit=1)
                    if not account:
                        _logger.warning("Webhook Business sem conta vinculada ao phone_number_id %s", phone_id)
                        continue
                    for message in value.get('messages', []):
                        msg_type = message.get('type')
                        if msg_type == 'text':
                            body = message.get('text', {}).get('body') or ''
                        elif msg_type == 'interactive':
                            body = message.get('interactive', {}).get('body', {}).get('text') or '[interativo]'
                        else:
                            body = '[mensagem não-texto]'
                        from_phone = message.get('from')
                        to_phone = message.get('to')
                        partner = env['res.partner'].search([
                            '|',
                            ('phone', 'ilike', from_phone),
                            ('mobile', 'ilike', from_phone),
                        ], limit=1)

                        timestamp = message.get('timestamp')
                        wa_dt = fields.Datetime.now()
                        if timestamp:
                            try:
                                wa_dt = fields.Datetime.to_string(datetime.utcfromtimestamp(int(timestamp)))
                            except Exception:
                                pass

                        record = env['bhz.wa.message'].create({
                            "account_id": account.id,
                            "direction": "in",
                            "partner_id": partner.id if partner else False,
                            "remote_jid": f"{from_phone}@s.whatsapp.net",
                            "remote_phone": from_phone,
                            "wa_from": from_phone,
                            "wa_to": to_phone,
                            "body": body,
                            "state": "new",
                            "provider": "business",
                            "wa_timestamp": wa_dt,
                            "payload_json": json.dumps(message),
                        })

                        if partner:
                            partner.message_post(body=f"📲 WA Business (IN): {record.body}")

                        account.with_context(bypass_limits=True).try_ai_autoreply(record)

            return {"status": "ok"}
        except Exception as e:
            _logger.exception("Business inbound error: %s", e)
            return {"status": "error", "message": str(e)}
