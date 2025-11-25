from odoo import api


def post_init_hook(env):
    """Renomeia o OdooBot para Assistente BHZ após instalar o módulo (Odoo 19)."""

    # Garante superusuário
    env = env.sudo()
    User = env["res.users"]

    # Tenta pegar pelo xml_id padrão do bot
    bot_user = env.ref("mail_bot.user_odoobot", raise_if_not_found=False)

    # Se não achar pelo xml_id, procura pelo login
    if not bot_user:
        bot_user = User.search([("login", "=", "odoobot")], limit=1)

    # Se ainda não achar, tenta pelo nome
    if not bot_user:
        bot_user = User.search([("name", "=", "OdooBot")], limit=1)

    if not bot_user:
        # Não encontrou o bot, não faz nada
        return

    new_name = "Assistente BHZ"

    # Altera o nome do usuário
    bot_user.name = new_name

    # Altera também o nome do partner (é o que aparece no chat)
    if bot_user.partner_id:
        bot_user.partner_id.name = new_name
