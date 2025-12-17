# -*- coding: utf-8 -*-
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BhzWaMessage(models.Model):
    _name = "bhz.wa.message"
    _description = "Mensagem WhatsApp"
    _order = "id desc"
    _rec_name = "body"

    partner_id = fields.Many2one("res.partner", string="Contato", index=True, ondelete="set null")
    account_id = fields.Many2one("bhz.wa.account", string="Conta", ondelete="cascade")
    session_id = fields.Many2one("bhz.wa.session", string="Sessão", ondelete="cascade")
    conversation_id = fields.Many2one(
        "bhz.wa.conversation",
        string="Conversa",
        ondelete="cascade",
    )

    provider = fields.Selection(
        [
            ("starter", "Starter"),
            ("business", "Business"),
        ],
        default="starter",
        required=True,
    )
    direction = fields.Selection(
        [
            ("in", "Entrada"),
            ("out", "Saída"),
        ],
        required=True,
        default="in",
    )
    state = fields.Selection(
        [
            ("queued", "Na fila"),
            ("sent", "Enviada"),
            ("delivered", "Entregue"),
            ("read", "Lida"),
            ("received", "Recebida"),
            ("error", "Erro"),
        ],
        default="received",
    )

    body = fields.Text("Mensagem")
    wa_from = fields.Char("De")
    wa_to = fields.Char("Para")
    is_group = fields.Boolean("Grupo?")
    external_message_id = fields.Char("ID externo")
    message_timestamp = fields.Float("Epoch")
    payload_json = fields.Text("Payload bruto")
    remote_jid = fields.Char("Remoto (JID)")
    remote_phone = fields.Char("Telefone remoto")

    is_me = fields.Boolean("Minha", compute="_compute_is_me", store=False)

    @api.depends("direction")
    def _compute_is_me(self):
        for record in self:
            record.is_me = record.direction == "out"

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        Conversation = self.env["bhz.wa.conversation"].sudo()
        for msg in messages:
            try:
                if msg.partner_id and (msg.session_id or msg.account_id):
                    conv = Conversation.get_or_create_from_message(msg)
                    msg.conversation_id = conv.id
            except Exception:
                _logger.exception("Erro ao vincular mensagem à conversa WhatsApp")
        return messages

    def action_rebuild_conversations(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Ação permitida apenas para administradores."))
        self.env["bhz.wa.conversation"].sudo().recompute_from_all_messages()
        return True

    @api.model
    def create_from_starter_payload(self, payload, account=None):
        payload = payload or {}
        session_code = payload.get("session") or payload.get("session_id")
        Session = self.env["bhz.wa.session"].sudo()
        session = Session.search([("session_id", "=", session_code)], limit=1) if session_code else Session.browse()
        account = account or (session.account_id if session else False)

        remote_jid = (payload.get("remote_jid") or "").strip()
        phone = remote_jid.replace("@s.whatsapp.net", "").replace("@g.us", "").strip()
        if not phone:
            phone = (payload.get("from") or "").strip()

        Partner = self.env["res.partner"].sudo()
        partner = False
        if phone:
            partner = Partner.search(["|", ("mobile", "=", phone), ("phone", "=", phone)], limit=1)
            if not partner:
                partner = Partner.create({
                    "name": phone,
                    "mobile": phone,
                    "phone": phone,
                })

        direction = "out" if payload.get("from_me") else "in"
        wa_from = phone if direction == "in" else (account.starter_last_number if account else "")
        wa_to = (account.starter_last_number if account else "") if direction == "in" else phone

        timestamp_ms = payload.get("timestamp")
        try:
            message_ts = float(timestamp_ms) / 1000.0 if timestamp_ms else 0.0
        except Exception:
            message_ts = 0.0

        vals = {
            "partner_id": partner.id if partner else False,
            "account_id": account.id if account else False,
            "session_id": session.id if session else False,
            "provider": payload.get("provider") or "starter",
            "direction": direction,
            "state": "sent" if direction == "out" else "received",
            "body": payload.get("body") or "",
            "wa_from": wa_from,
            "wa_to": wa_to,
            "external_message_id": payload.get("message_id"),
            "message_timestamp": message_ts,
            "payload_json": json.dumps(payload),
            "remote_jid": remote_jid or False,
            "remote_phone": phone or False,
            "is_group": bool(remote_jid and remote_jid.endswith("@g.us")),
        }
        return self.sudo().create(vals)
