# -*- coding: utf-8 -*-
import logging
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BhzWaConversation(models.Model):
    _name = "bhz.wa.conversation"
    _description = "Conversa WhatsApp"
    _order = "last_message_date desc, id desc"

    name = fields.Char("Nome", compute="_compute_name", store=True)
    partner_id = fields.Many2one("res.partner", string="Contato", index=True)
    account_id = fields.Many2one("bhz.wa.account", string="Conta")
    session_id = fields.Many2one("bhz.wa.session", string="Sessão")
    last_message = fields.Text("Última mensagem")
    last_message_date = fields.Datetime("Data da última")
    unread_count = fields.Integer("Não lidas", default=0)
    message_ids = fields.One2many("bhz.wa.message", "conversation_id", string="Mensagens")
    composer_text = fields.Text(string="Mensagem a enviar")

    @api.depends("partner_id")
    def _compute_name(self):
        for record in self:
            record.name = record.partner_id.display_name or "Conversa"

    @api.model
    def _get_or_create_from_partner(self, partner_id, account_id=False, session_id=False):
        domain = [("partner_id", "=", partner_id)]
        if account_id:
            domain.append(("account_id", "=", account_id))
        conv = self.search(domain, limit=1)
        if not conv:
            conv = self.create(
                {
                    "partner_id": partner_id,
                    "account_id": account_id or False,
                    "session_id": session_id or False,
                }
            )
        return conv

    def _bump_last_message(self, body):
        self.write(
            {
                "last_message": body or "",
                "last_message_date": fields.Datetime.now(),
            }
        )

    def _inc_unread(self, n=1):
        for rec in self:
            rec.unread_count = (rec.unread_count or 0) + n

    def action_mark_read(self):
        self.write({"unread_count": 0})

    def action_send_text(self, text=False):
        icp = self.env["ir.config_parameter"].sudo()
        base = (icp.get_param("starter_service.base_url") or "").rstrip("/")
        if not base:
            raise UserError(_("Parâmetro 'starter_service.base_url' ausente."))

        for conv in self:
            message = text or conv.composer_text or self.env.context.get("text")
            if not message:
                continue

            to = (conv.partner_id.mobile or conv.partner_id.phone or "").strip()
            if not to:
                raise UserError(_("Contato sem telefone configurado."))

            url = f"{base}/api/messages"
            payload = {"to": to, "type": "text", "body": message}
            try:
                resp = requests.post(url, json=payload, timeout=30)
            except Exception as exc:
                raise UserError(_("Falha ao enviar: %s") % exc)

            if resp.status_code not in (200, 201):
                raise UserError(_("Erro do Starter (%s): %s") % (resp.status_code, resp.text))

            self.env["bhz.wa.message"].create(
                {
                    "conversation_id": conv.id,
                    "partner_id": conv.partner_id.id,
                    "account_id": conv.account_id.id if conv.account_id else False,
                    "session_id": conv.session_id.id if conv.session_id else False,
                    "provider": "starter",
                    "direction": "out",
                    "state": "queued",
                    "body": message,
                    "wa_to": to,
                }
            )
            conv._bump_last_message(message)
            conv.composer_text = False
        return True
