# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BhzWaWebhookStarter(http.Controller):

    @http.route('/bhz_whatsapp/inbound', type='json', auth='none', csrf=False, methods=['POST'])
    def inbound(self, **payload):
        try:
            if not payload.get('session') or not payload.get('eventType'):
                _logger.warning("Starter webhook payload incompleto: %s", payload)
                return {'ok': True}

            env = request.env['bhz.wa.message'].sudo()
            env.create({
                'session_id': payload.get('session'),
                'event_type': payload.get('eventType'),
                'remote_id': payload.get('remote_jid'),
                'message': payload.get('message'),
                'timestamp': payload.get('timestamp'),
                'direction': payload.get('direction', 'in'),
            })
        except Exception as e:
            _logger.error("Webhook inbound error: %s", e)
            return {'ok': True}

        return {'ok': True}
