# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BhzWaConversation(models.Model):
    _name = "bhz.wa.conversation"
    _description = "Conversa WhatsApp"
    _order = "is_pinned desc, last_message_date desc, id desc"

    name = fields.Char(string="Nome")
    partner_id = fields.Many2one("res.partner", string="Contato", ondelete="set null")
    session_id = fields.Many2one("bhz.wa.session", string="Sessão", ondelete="cascade")
    account_id = fields.Many2one("bhz.wa.account", string="Conta", ondelete="cascade")
    last_message_id = fields.Many2one("bhz.wa.message", string="Última mensagem", ondelete="set null")
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
            ("account_id", "=", message.account_id.id if message.account_id else False),
        ]

    @api.model
    def get_or_create_from_message(self, message):
        conversation = self.search(self._get_conversation_domain(message), limit=1)
        if not conversation:
            partner = message.partner_id
            name = partner.display_name if partner else (message.wa_from or _("Conversa"))
            conversation = self.create({
                "name": name,
                "partner_id": partner.id if partner else False,
                "session_id": message.session_id.id if message.session_id else False,
                "account_id": message.account_id.id if message.account_id else False,
            })
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
        for conv in self:
            conv.sudo().write({"unread_count": 0})

    @api.model
    def recompute_from_all_messages(self):
        Message = self.env["bhz.wa.message"].sudo()
        self.sudo().search([]).write({
            'last_message_id': False,
            'last_message_body': False,
            'last_message_date': False,
            'last_direction': False,
            'unread_count': 0,
        })
        msgs = Message.search([], order="create_date asc")
        for msg in msgs:
            try:
                conv = self.get_or_create_from_message(msg)
                msg.conversation_id = conv.id
            except Exception:
                continue

    @api.constrains('partner_session_key')
    def _check_partner_session_key_unique(self):
        for rec in self:
            if not rec.partner_session_key:
                continue
            domain=[('id','!=',rec.id),('partner_session_key','=',rec.partner_session_key)]
            if self.search_count(domain):
                raise ValidationError(_('partner_session_key must be unique'))
