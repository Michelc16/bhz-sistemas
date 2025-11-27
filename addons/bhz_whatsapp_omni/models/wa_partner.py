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
        """Retorna (ou cria) um canal do Discuss vinculado ao contato."""
        MailChannel = self.env["mail.channel"].sudo()
        user_partner = self.env.user.partner_id
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
                commands = [(4, partner.id)]
                if user_partner:
                    commands.append((4, user_partner.id))
                channel = MailChannel.create(
                    {
                        "name": partner.display_name
                        or partner.name
                        or partner.mobile
                        or "WhatsApp",
                        "channel_type": "chat",
                        "channel_partner_ids": commands,
                        "wa_partner_id": partner.id,
                        "wa_is_whatsapp": True,
                    }
                )
            partner.wa_channel_id = channel.id
        return self.mapped("wa_channel_id")
