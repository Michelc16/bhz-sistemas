# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BhzWaWebhookStarter(http.Controller):

    @http.route([
        '/bhz/whatsapp/starter/inbound',
        '/bhz/wa/inbound',
    ], type='json', auth='public', methods=['POST'], csrf=False)
    def inbound(self, **kwargs):
        icp = request.env['ir.config_parameter'].sudo()
        expected = (icp.get_param('starter_service.secret') or '').strip()
        got = (request.httprequest.headers.get('X-Webhook-Secret') or '').strip()
        if expected and expected != got:
            _logger.warning("Starter inbound: secret inválido")
            return {'ok': False, 'error': 'unauthorized'}

        payload = request.jsonrequest or {}
        _logger.info("Starter webhook payload: %s", payload)
        event_type = (payload.get('eventType') or payload.get('event_type') or 'message').lower()
        if event_type != 'message':
            return {'ok': True}

        Message = request.env['bhz.wa.message'].sudo()
        try:
            message = Message.create_from_starter_payload(payload)
        except Exception as exc:
            _logger.exception("Erro ao registrar mensagem Starter: %s", exc)
            return {'ok': False, 'error': 'server_error'}

        try:
            if message.conversation_id:
                request.env['bus.bus'].sudo().sendone('bhz_wa_inbox', {
                    'type': 'new_message',
                    'message_id': message.id,
                    'conversation_id': message.conversation_id.id,
                })
        except Exception as exc:
            _logger.exception("Erro ao publicar mensagem no bus: %s", exc)

        return {'ok': True}
