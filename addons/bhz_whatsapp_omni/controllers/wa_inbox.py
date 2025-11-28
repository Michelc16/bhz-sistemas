# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BhzWaInboxController(http.Controller):

    @http.route('/bhz/wa/inbox/conversations', type='json', auth='user', methods=['POST'])
    def conversations(self):
        env = request.env
        conversations = env['bhz.wa.conversation'].sudo().search([], order='is_pinned desc, last_message_date desc', limit=80)
        data = []
        for conv in conversations:
            data.append({
                'id': conv.id,
                'name': conv.name or (conv.partner_id.display_name if conv.partner_id else ''),
                'last_message_body': conv.last_message_body,
                'last_message_date': conv.last_message_date,
                'last_direction': conv.last_direction,
                'unread_count': conv.unread_count,
                'partner_name': conv.partner_id.display_name if conv.partner_id else '',
                'partner_avatar': False,
                'is_pinned': conv.is_pinned,
            })
        return {'conversations': data}

    @http.route('/bhz/wa/inbox/messages', type='json', auth='user', methods=['POST'])
    def messages(self, conversation_id, limit=50, offset=0):
        env = request.env
        conversation = env['bhz.wa.conversation'].sudo().browse(conversation_id)
        if not conversation.exists():
            return {'messages': []}
        msgs = env['bhz.wa.message'].sudo().search(
            [('conversation_id', '=', conversation.id)],
            order='create_date asc',
            limit=limit,
            offset=offset,
        )
        data = []
        for msg in msgs:
            data.append({
                'id': msg.id,
                'body': msg.body,
                'direction': msg.direction,
                'create_date': msg.create_date,
                'partner_name': msg.partner_id.display_name if msg.partner_id else '',
                'is_me': msg.direction == 'out',
            })
        return {'messages': data}

    @http.route('/bhz/wa/inbox/send_message', type='json', auth='user', methods=['POST'])
    def send_message(self, conversation_id, body):
        env = request.env
        conversation = env['bhz.wa.conversation'].sudo().browse(conversation_id)
        if not conversation.exists():
            return {'error': 'conversation_not_found'}
        if not body:
            return {'error': 'empty'}
        account = conversation.account_id
        if not account:
            return {'error': 'missing_account'}
        partner = conversation.partner_id
        if not partner:
            return {'error': 'missing_partner'}
        to_number = (partner.mobile or partner.phone or '').strip()
        if not to_number:
            return {'error': 'missing_number'}
        try:
            msg = account.send_text(to_number, body, partner_id=partner.id, session_id=conversation.session_id.id)
            if msg:
                msg.conversation_id = conversation.id
                self._send_bus_event(msg)
            return {'message_id': msg.id, 'status': 'sent'}
        except Exception as exc:
            _logger.exception('Erro ao enviar mensagem do inbox: %s', exc)
            return {'error': 'send_failed'}

    @http.route('/bhz/wa/inbox/mark_read', type='json', auth='user', methods=['POST'])
    def mark_read(self, conversation_id):
        conversation = request.env['bhz.wa.conversation'].sudo().browse(conversation_id)
        if conversation.exists():
            conversation.mark_read()
        return {'status': 'ok'}

    @http.route('/bhz/wa/inbox/channel', type='json', auth='user', methods=['POST'])
    def channel(self):
        return {'channel': 'bhz_wa_inbox'}

    def _send_bus_event(self, message):
        try:
            bus = request.env['bus.bus'].sudo()
            bus.sendone('bhz_wa_inbox', {
                'type': 'new_message',
                'message_id': message.id,
                'conversation_id': message.conversation_id.id,
            })
        except Exception as exc:
            _logger.exception('Erro ao publicar evento no bus: %s', exc)
