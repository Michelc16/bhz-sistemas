# -*- coding: utf-8 -*-
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BhzWaInboxController(http.Controller):

    @http.route('/bhz/wa/inbox/conversations', type='jsonrpc', auth='user', methods=['POST'])
    def conversations(self):
        conversations = request.env['bhz.wa.conversation'].sudo().search([], order='is_pinned desc, last_message_date desc', limit=100)
        data = []
        for conv in conversations:
            data.append({
                'id': conv.id,
                'name': conv.name or (conv.partner_id.display_name if conv.partner_id else ''),
                'last_message_body': conv.last_message_body,
                'last_message_date': fields.Datetime.to_string(conv.last_message_date) if conv.last_message_date else False,
                'last_direction': conv.last_direction,
                'unread_count': conv.unread_count,
                'partner_name': conv.partner_id.display_name if conv.partner_id else '',
                'is_pinned': conv.is_pinned,
            })
        return {'conversations': data}

    @http.route('/bhz/wa/inbox/messages', type='jsonrpc', auth='user', methods=['POST'])
    def messages(self, conversation_id, limit=50, offset=0):
        conversation = request.env['bhz.wa.conversation'].sudo().browse(conversation_id)
        if not conversation.exists():
            return {'messages': []}
        msgs = request.env['bhz.wa.message'].sudo().search(
            [('conversation_id', '=', conversation.id)],
            order='create_date asc',
            limit=limit,
            offset=offset,
        )
        data = []
        for msg in msgs:
            data.append({
                'id': msg.id,
                'body': msg.body or '',
                'direction': msg.direction,
                'create_date': fields.Datetime.to_string(msg.create_date) if msg.create_date else False,
                'partner_name': msg.partner_id.display_name if msg.partner_id else '',
                'is_me': msg.direction == 'out',
            })
        return {'messages': data}

    @http.route('/bhz/wa/inbox/send_message', type='jsonrpc', auth='user', methods=['POST'])
    def send_message(self, conversation_id, body):
        conversation = request.env['bhz.wa.conversation'].sudo().browse(conversation_id)
        if not conversation.exists():
            return {'error': 'conversation_not_found'}
        if not body:
            return {'error': 'empty'}
        account = conversation.account_id
        partner = conversation.partner_id
        number = (partner.mobile or partner.phone or '').strip() if partner else ''
        if not account or not partner or not conversation.session_id or not number:
            return {'error': 'configuration_error'}
        try:
            message = account.send_text(number, body, partner_id=partner.id, session_id=conversation.session_id.id)
            if message:
                message.conversation_id = conversation.id
                self._send_bus_event(message)
                return {
                    'message': {
                        'id': message.id,
                        'body': message.body,
                        'direction': message.direction,
                        'create_date': fields.Datetime.to_string(message.create_date),
                        'is_me': True,
                    }
                }
        except Exception as exc:
            _logger.exception('Erro ao enviar mensagem do inbox: %s', exc)
            return {'error': 'send_failed'}
        return {'error': 'send_failed'}

    @http.route('/bhz/wa/inbox/mark_read', type='jsonrpc', auth='user', methods=['POST'])
    def mark_read(self, conversation_id):
        conversation = request.env['bhz.wa.conversation'].sudo().browse(conversation_id)
        if conversation.exists():
            conversation.mark_read()
        return {'status': 'ok'}

    def _send_bus_event(self, message):
        try:
            if message.conversation_id:
                request.env['bus.bus'].sudo().sendone('bhz_wa_inbox', {
                    'type': 'new_message',
                    'message_id': message.id,
                    'conversation_id': message.conversation_id.id,
                })
        except Exception as exc:
            _logger.exception('Erro ao publicar evento no bus: %s', exc)
