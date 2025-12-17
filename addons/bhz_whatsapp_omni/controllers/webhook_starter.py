# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BhzWaWebhookStarter(http.Controller):

    @staticmethod
    def _get_account_from_headers():
        secret = (request.httprequest.headers.get('X-Webhook-Secret') or '').strip()
        if not secret:
            return False
        Account = request.env['bhz.wa.account'].sudo()
        account = Account.search([('starter_secret', '=', secret)], limit=1)
        if not account:
            _logger.warning("Starter inbound: segredo inválido recebido.")
        return account

    @staticmethod
    def _validate_session(account, payload):
        session_code = payload.get('session') or payload.get('session_id')
        if not session_code:
            return True
        expected = account.starter_session_id
        if expected and session_code != expected:
            _logger.warning("Starter inbound: sessão %s diferente de %s.", session_code, expected)
            return False
        return True

    @http.route(['/bhz_wa/starter/inbound', '/bhz/wa/inbound'], type='json', auth='public', methods=['POST'], csrf=False)
    def inbound(self, **kwargs):
        account = self._get_account_from_headers()
        if not account:
            return {'ok': False, 'error': 'unauthorized'}

        payload = request.jsonrequest or {}
        if not self._validate_session(account, payload):
            return {'ok': False, 'error': 'wrong_session'}

        _logger.info("Starter webhook payload: %s", payload)
        event_type = (payload.get('eventType') or payload.get('event_type') or 'message').lower()
        if event_type == 'status':
            account._handle_starter_status_webhook(payload)
            return {'ok': True}

        if event_type != 'message':
            return {'ok': True}

        Message = request.env['bhz.wa.message'].sudo()
        try:
            message = Message.create_from_starter_payload(payload, account=account)
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

        if message:
            account.message_post(
                body=f"Mensagem recebida de {message.remote_phone or message.remote_jid}"
            )

        return {'ok': True}
