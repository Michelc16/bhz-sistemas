# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    wa_channel_id = fields.Many2one(
        "mail.channel",
        string="Canal WhatsApp",
        help="Canal de conversa no Discuss vinculado a este contato WhatsApp.",
    )

    def get_or_create_wa_channel(self):
        """Retorna um mail.channel do tipo chat vinculado ao partner para WhatsApp."""
        MailChannel = self.env["mail.channel"].sudo()
        for partner in self:
            if partner.wa_channel_id:
                continue

            channel = MailChannel.search(
                [
                    ("channel_type", "=", "chat"),
                    ("wa_partner_id", "=", partner.id),
                ],
                limit=1,
            )
            if not channel:
                channel = MailChannel.create({
                    "name": partner.display_name or partner.name or partner.mobile or "WhatsApp",
                    "channel_type": "chat",
                    "channel_partner_ids": [(4, partner.id)],
                    "wa_partner_id": partner.id,
                    "wa_is_whatsapp": True,
                })
            partner.wa_channel_id = channel.id
        return self.mapped("wa_channel_id")
