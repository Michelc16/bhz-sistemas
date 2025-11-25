from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_odoobot(self):
        """
        Este método é chamado quando o Odoo configura o bot para um usuário novo.

        - Deixa o comportamento padrão (super)
        - Em seguida envia uma mensagem de boas-vindas no estilo BHZ
        """
        res = super()._init_odoobot()

        odoobot_partner = self.env.ref(
            "mail_bot.partner_odoobot", raise_if_not_found=False
        )
        if not odoobot_partner:
            return res

        Channel = self.env["discuss.channel"].sudo()

        for user in self:
            if not user.partner_id:
                continue

            # pega o chat privado entre usuário e bot
            channel = Channel.search(
                [
                    ("channel_type", "=", "chat"),
                    ("channel_partner_ids", "in", user.partner_id.id),
                    ("channel_partner_ids", "in", odoobot_partner.id),
                ],
                limit=1,
            )

            if not channel:
                continue

            # mensagem BHZ
            body = """
            <p>Olá! 👋 Eu sou o <b>Assistente BHZ</b>.</p>
            <p>
                Estou aqui para te ajudar com:
            </p>
            <ul>
                <li>💼 Vendas e orçamentos</li>
                <li>📦 Estoque e movimentações</li>
                <li>🛒 Integrações com Marketplace (Magalu, Mercado Livre, etc.)</li>
                <li>🤖 Dúvidas sobre automações e módulos BHZ</li>
            </ul>
            <p>
                Me envie uma pergunta ou diga o que você quer fazer, e eu te guio pelo sistema. 🚀
            </p>
            """

            channel.message_post(
                body=body,
                author_id=odoobot_partner.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

        return res
