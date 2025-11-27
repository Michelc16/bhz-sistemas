# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        MailChannel = self.env["mail.channel"]

        for msg, vals in zip(records, vals_list):
            model = vals.get("model") or msg.model
            res_id = vals.get("res_id") or msg.res_id
            message_type = vals.get("message_type") or msg.message_type

            if model != "mail.channel" or not res_id:
                continue
            if message_type != "comment":
                continue

            if self.env.context.get("bhz_wa_skip_outbound"):
                continue

            channel = MailChannel.browse(res_id)
            if not channel or not channel.wa_is_whatsapp:
                continue
            try:
                channel._send_whatsapp_from_mail_message(msg)
            except Exception as exc:
                _logger.exception("Erro ao enviar msg WhatsApp a partir do Discuss: %s", exc)
        return records
