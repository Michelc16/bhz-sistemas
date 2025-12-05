import json
import logging
from datetime import datetime

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BHZWABusinessWebhook(http.Controller):

    @http.route('/bhz_wa/business/webhook', type='http', auth='public', csrf=False, methods=['GET'])
    def verify(self, **params):
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
        payload = payload or request.jsonrequest or {}
        try:
            env = request.env.sudo()
            Account = env['bhz.wa.account']
            Message = env['bhz.wa.message']
            Partner = env['res.partner']
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
                        partner = Partner.search([
                            '|',
                            ('phone', '=', from_phone),
                            ('mobile', '=', from_phone),
                        ], limit=1)
                        if not partner:
                            partner = Partner.create({
                                'name': from_phone,
                                'mobile': from_phone,
                                'phone': from_phone,
                            })

                        timestamp = message.get('timestamp')
                        wa_dt = fields.Datetime.now()
                        if timestamp:
                            try:
                                wa_dt = fields.Datetime.to_string(datetime.utcfromtimestamp(int(timestamp)))
                            except Exception:
                                pass

                        record = Message.create({
                            "partner_id": partner.id,
                            "account_id": account.id,
                            "provider": "business",
                            "direction": "in",
                            "state": "received",
                            "body": body,
                            "wa_from": from_phone,
                            "wa_to": to_phone,
                            "remote_jid": f"{from_phone}@s.whatsapp.net" if from_phone else False,
                            "remote_phone": from_phone,
                            "external_message_id": message.get('id'),
                            "message_timestamp": float(timestamp or 0.0),
                            "payload_json": json.dumps(message),
                        })

                        try:
                            request.env['bus.bus'].sudo().sendone('bhz_wa_inbox', {
                                'type': 'new_message',
                                'message_id': record.id,
                                'conversation_id': record.conversation_id.id,
                            })
                        except Exception as exc:
                            _logger.exception("Erro ao publicar mensagem Business no bus: %s", exc)

                        account.with_context(bypass_limits=True).try_ai_autoreply(record)

            return {"status": "ok"}
        except Exception as e:
            _logger.exception("Business inbound error: %s", e)
            return {"status": "error", "message": str(e)}
