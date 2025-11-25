from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Renomeia o OdooBot para Assistente BHZ após instalar o módulo."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    User = env["res.users"].sudo()

    # Tenta pegar pelo xml_id padrão do bot
    bot_user = env.ref("mail_bot.user_odoobot", raise_if_not_found=False)

    if not bot_user:
        bot_user = User.search([("login", "=", "odoobot")], limit=1)

    if not bot_user:
        bot_user = User.search([("name", "=", "OdooBot")], limit=1)

    if not bot_user:
        return  # não achou o bot, não faz nada

    new_name = "Assistente BHZ"

    bot_user.name = new_name
    if bot_user.partner_id:
        bot_user.partner_id.name = new_name