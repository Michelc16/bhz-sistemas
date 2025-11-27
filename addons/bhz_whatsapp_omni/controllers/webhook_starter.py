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
            return {'ok': False, 'error': 'forbidden'}

        payload = request.jsonrequest or {}
        if payload.get('event') != 'message' or not payload.get('message'):
            return {'ok': True}

        msg = payload['message']
        phone_from = (msg.get('from') or '').strip()
        phone_to = (msg.get('to') or '').strip()
        session_identifier = payload.get('session_id') or msg.get('session_id') or ''
        text = msg.get('body') or ''
        ts = msg.get('timestamp') or 0.0
        is_group = bool(msg.get('is_group'))
        contact_name = msg.get('contact_name') or phone_from

        env = request.env.sudo()
        Account = env['bhz.wa.account']
        Session = env['bhz.wa.session']
        account = False
        if session_identifier:
            account = Account.search([('starter_session_id', '=', session_identifier)], limit=1)
        if not account:
            account = Account.search([('mode', '=', 'starter')], limit=1)

        session = False
        if session_identifier:
            session = Session.search([('session_id', '=', session_identifier)], limit=1)

        Partner = env['res.partner']
        partner = Partner.search([
            '|',
            ('mobile', '=', phone_from),
            ('phone', '=', phone_from),
        ], limit=1)
        if not partner:
            partner = Partner.create({
                'name': contact_name or phone_from or 'Contato WhatsApp',
                'mobile': phone_from or False,
                'phone': phone_from or False,
            })

        Conv = env['bhz.wa.conversation']
        conv = Conv._get_or_create_from_partner(
            partner_id=partner.id,
            account_id=account.id if account else False,
            session_id=session.id if session else False,
        )

        Message = env['bhz.wa.message']
        message_rec = Message.create({
            'conversation_id': conv.id,
            'partner_id': partner.id,
            'account_id': account.id if account else False,
            'session_id': session.id if session else False,
            'provider': 'starter',
            'direction': 'in',
            'state': 'received',
            'body': text,
            'wa_from': phone_from,
            'wa_to': phone_to,
            'is_group': is_group,
            'external_message_id': msg.get('id'),
            'message_timestamp': float(ts or 0.0),
            'payload_json': request.jsonrequest and json.dumps(request.jsonrequest) or False,
        })

        conv._bump_last_message(text)
        conv._inc_unread()

        partner.get_or_create_wa_channel()
        channel = partner.wa_channel_id
        if channel:
            body_html = (text or "").replace("\n", "<br/>")
            channel.with_context(mail_create_nosubscribe=True, bhz_wa_skip_outbound=True).message_post(
                body=body_html,
                author_id=partner.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

        return {'ok': True}
