# -*- coding: utf-8 -*-
import logging

import requests
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class MailChannel(models.Model):
    _inherit = "mail.channel"

    wa_is_whatsapp = fields.Boolean(string="Canal WhatsApp", default=False)
    wa_partner_id = fields.Many2one("res.partner", string="Contato WhatsApp", ondelete="set null")

    def _get_starter_base_url(self):
        icp = self.env["ir.config_parameter"].sudo()
        base = (icp.get_param("starter_service.base_url") or "").strip()
        if not base:
            raise UserError(_("Parâmetro 'starter_service.base_url' não configurado."))
        return base.rstrip("/")

    def _send_whatsapp_from_mail_message(self, message):
        """Envia a mensagem do Discuss para o WhatsApp via Starter."""
        self.ensure_one()
        if not self.wa_is_whatsapp or not self.wa_partner_id:
            return
        partner = self.wa_partner_id
        to = (partner.mobile or partner.phone or "").strip()
        if not to:
            raise UserError(_("Contato WhatsApp sem número de telefone."))

        base = self._get_starter_base_url()
        url = f"{base}/api/messages"
        body_plain = html2plaintext(message.body or "") if message.body else ""
        payload = {
            "to": to,
            "type": "text",
            "body": body_plain,
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
        except Exception as exc:
            _logger.exception("Erro ao enviar mensagem ao Starter")
            raise UserError(_("Falha ao conectar ao servidor WhatsApp: %s") % exc)

        if resp.status_code not in (200, 201):
            raise UserError(_("Starter retornou erro (%s): %s") % (resp.status_code, resp.text))

        self.env["bhz.wa.message"].sudo().create(
            {
                "conversation_id": False,
                "partner_id": partner.id,
                "account_id": False,
                "session_id": False,
                "provider": "starter",
                "direction": "out",
                "state": "queued",
                "body": body_plain,
                "wa_from": "",
                "wa_to": to,
            }
        )
