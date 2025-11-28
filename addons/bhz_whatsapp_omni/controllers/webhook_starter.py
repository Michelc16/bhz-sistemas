# -*- coding: utf-8 -*-
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
            return {'ok': False, 'error': 'forbidden'}

        payload = request.jsonrequest or {}
        if payload.get('event') != 'message' or not payload.get('message'):
            return {'ok': True}

        msg = payload['message']
        phone_from = (msg.get('from') or '').strip()
        phone_to = (msg.get('to') or '').strip()
        text = msg.get('body') or ''
        ts = msg.get('timestamp')
        is_group = bool(msg.get('is_group'))
        contact_name = msg.get('contact_name') or phone_from

        env = request.env.sudo()
        Partner = env['res.partner']
        Account = env['bhz.wa.account']
        Session = env['bhz.wa.session']
        Message = env['bhz.wa.message']

        account = Account.search([], limit=1)
        session = Session.search([], limit=1)

        partner = Partner.search([('mobile', '=', phone_from)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': contact_name or phone_from or 'Contato WhatsApp',
                'mobile': phone_from or False,
                'phone': phone_from or False,
            })

        message = Message.create({
            'partner_id': partner.id,
            'account_id': account.id if account else False,
            'session_id': session.id if session else False,
            'provider': 'starter',
            'direction': 'in',
            'body': text,
            'wa_from': phone_from,
            'wa_to': phone_to,
            'is_group': is_group,
            'external_message_id': msg.get('id'),
            'message_timestamp': ts,
            'state': 'received',
        })

        try:
            request.env['bus.bus'].sudo().sendone('bhz_wa_inbox', {
                'type': 'new_message',
                'message_id': message.id,
                'conversation_id': message.conversation_id.id,
            })
        except Exception as exc:
            _logger.exception("Erro ao publicar mensagem no bus: %s", exc)

        return {'ok': True}
