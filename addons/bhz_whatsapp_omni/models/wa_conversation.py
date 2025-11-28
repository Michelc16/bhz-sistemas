# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BhzWaConversation(models.Model):
    _name = "bhz.wa.conversation"
    _description = "Conversa WhatsApp"
    _order = "is_pinned desc, last_message_date desc, id desc"
    _sql_constraints = [
        (
            "partner_session_unique",
            "unique(partner_id, session_id)",
            "Já existe uma conversa para este contato e sessão.",
        )
    ]

    name = fields.Char(string="Nome")
    partner_id = fields.Many2one("res.partner", string="Contato")
    session_id = fields.Many2one("bhz.wa.session", string="Sessão")
    account_id = fields.Many2one("bhz.wa.account", string="Conta")
    last_message_id = fields.Many2one("bhz.wa.message", string="Última mensagem")
    last_message_body = fields.Char(string="Conteúdo da última mensagem")
    last_message_date = fields.Datetime(string="Data da última mensagem")
    last_direction = fields.Selection(
        [
            ("in", "Entrada"),
            ("out", "Saída"),
        ],
        string="Direção",
    )
    unread_count = fields.Integer(string="Não lidas", default=0)
    is_pinned = fields.Boolean(string="Fixada", default=False)
    is_archived = fields.Boolean(string="Arquivada", default=False)
    state = fields.Selection(
        [
            ("active", "Ativa"),
            ("closed", "Encerrada"),
        ],
        default="active",
    )

    @api.model
    def _get_conversation_domain(self, message):
        return [
            ("partner_id", "=", message.partner_id.id if message.partner_id else False),
            ("session_id", "=", message.session_id.id if message.session_id else False),
        ]

    @api.model
    def get_or_create_from_message(self, message):
        conversation = self.search(self._get_conversation_domain(message), limit=1)
        if not conversation:
            values = {
                "name": message.partner_id.display_name or message.wa_from or _("Conversa"),
                "partner_id": message.partner_id.id if message.partner_id else False,
                "session_id": message.session_id.id if message.session_id else False,
                "account_id": message.account_id.id if message.account_id else False,
            }
            conversation = self.create(values)
        conversation._update_from_message(message)
        return conversation

    def _update_from_message(self, message):
        self.ensure_one()
        vals = {
            "last_message_id": message.id,
            "last_message_body": (message.body or "")[:250],
            "last_message_date": message.create_date,
            "last_direction": message.direction,
        }
        if message.direction == "in":
            vals["unread_count"] = (self.unread_count or 0) + 1
        self.sudo().write(vals)

    def mark_read(self):
        self.write({"unread_count": 0})
