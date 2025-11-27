# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzWaMessage(models.Model):
    _name = "bhz.wa.message"
    _description = "Mensagem WhatsApp"
    _order = "id desc"
    _rec_name = "body"

    partner_id = fields.Many2one("res.partner", string="Contato", index=True)
    account_id = fields.Many2one("bhz.wa.account", string="Conta")
    session_id = fields.Many2one("bhz.wa.session", string="Sessão")

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
