# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BhzWaMessage(models.Model):
    _name = "bhz.wa.message"
    _description = "Mensagem WhatsApp"
    _order = "id desc"
    _rec_name = "body"

    partner_id = fields.Many2one("res.partner", string="Contato", index=True)
    account_id = fields.Many2one("bhz.wa.account", string="Conta")
    session_id = fields.Many2one("bhz.wa.session", string="Sessão")
    conversation_id = fields.Many2one(
        "bhz.wa.conversation",
        string="Conversa",
        ondelete="set null",
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
                if msg.partner_id and msg.session_id:
                    conv = Conversation.get_or_create_from_message(msg)
                    msg.conversation_id = conv.id
            except Exception:
                _logger.exception("Erro ao vincular mensagem à conversa WhatsApp")
        return messages

    def action_rebuild_conversations(self):
        self.env["bhz.wa.conversation"].sudo().recompute_from_all_messages()
        return True
