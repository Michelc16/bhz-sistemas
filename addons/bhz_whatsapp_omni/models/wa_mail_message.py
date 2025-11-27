# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)

        for msg in messages:
            if msg.model != "mail.channel":
                continue
            if msg.message_type != "comment":
                continue
            if self.env.context.get("bhz_wa_skip_outbound"):
                continue

            channel = self.env["mail.channel"].browse(msg.res_id)
            try:
                if channel.wa_is_whatsapp:
                    channel._send_whatsapp_from_mail_message(msg)
            except Exception as e:
                _logger.exception("Erro ao enviar msg WhatsApp a partir do Discuss: %s", e)
        return messages
