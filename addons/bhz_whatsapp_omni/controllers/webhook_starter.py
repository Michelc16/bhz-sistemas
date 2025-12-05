# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BhzWaWebhookStarter(http.Controller):

    @http.route('/bhz/whatsapp/starter/inbound', type='json', auth='public', methods=['POST'], csrf=False)
    def inbound(self, **kwargs):
        icp = request.env['ir.config_parameter'].sudo()
        expected = (icp.get_param('starter_service.secret') or '').strip()
        got = (request.httprequest.headers.get('X-Webhook-Secret') or '').strip()
        if expected and expected != got:
            _logger.warning("Starter inbound: secret inválido")
            return {'error': 'forbidden'}

        payload = request.jsonrequest or {}
        _logger.info("Starter webhook payload: %s", payload)

        session_code = (payload.get('session') or payload.get('session_id') or '').strip()
        phone_from = (payload.get('from') or '').strip()
        text = (payload.get('message') or payload.get('body') or '').strip()
        ts = payload.get('timestamp')
        try:
            ts = float(ts) if ts is not None else False
        except Exception:
            ts = False

        if not session_code or not phone_from or not text:
            _logger.warning("Starter inbound payload incompleto: %s", payload)
            return {'error': 'invalid_payload'}

        env = request.env.sudo()
        Session = env['bhz.wa.session']
        session = Session.search([('session_id', '=', session_code)], limit=1)
        account = session.account_id if session else env['bhz.wa.account'].search([], limit=1)

        partner = env['res.partner'].search([
            '|', ('mobile', '=', phone_from), ('phone', '=', phone_from)
        ], limit=1)
        if not partner:
            partner = env['res.partner'].create({
                'name': phone_from,
                'mobile': phone_from,
                'phone': phone_from,
            })

        wa_to = ''
        if session and session.account_id and session.account_id.starter_last_number:
            wa_to = session.account_id.starter_last_number

        remote_jid = f"{phone_from}@s.whatsapp.net"
        message_vals = {
            'partner_id': partner.id,
            'account_id': account.id if account else False,
            'session_id': session.id if session else False,
            'provider': 'starter',
            'direction': 'in',
            'state': 'received',
            'body': text,
            'wa_from': phone_from,
            'wa_to': wa_to,
            'remote_jid': remote_jid,
            'remote_phone': phone_from,
            'external_message_id': payload.get('message_id'),
            'message_timestamp': ts or 0.0,
            'payload_json': json.dumps(payload),
        }

        message = env['bhz.wa.message'].create(message_vals)
        _logger.info("Mensagem WhatsApp registrada: %s", message.id)

        try:
            if message.conversation_id:
                request.env['bus.bus'].sudo().sendone('bhz_wa_inbox', {
                    'type': 'new_message',
                    'message_id': message.id,
                    'conversation_id': message.conversation_id.id,
                })
        except Exception as exc:
            _logger.exception("Erro ao publicar mensagem no bus: %s", exc)

        return {'status': 'ok'}
