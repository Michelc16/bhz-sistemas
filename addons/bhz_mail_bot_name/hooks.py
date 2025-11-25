from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """
    O Odoo 19 envia um 'env' limitado para o post_init_hook.
    Por isso, devemos recriar um Environment completo.
    """

    # recria o env real
    real_env = api.Environment(env.cr, SUPERUSER_ID, {})
    User = real_env["res.users"]

    # tenta pegar o OdooBot pelo XML-ID
    bot_user = real_env.ref("mail_bot.user_odoobot", raise_if_not_found=False)

    # fallback 1 — login
    if not bot_user:
        bot_user = User.search([("login", "=", "odoobot")], limit=1)

    # fallback 2 — nome original
    if not bot_user:
        bot_user = User.search([("name", "=", "OdooBot")], limit=1)

    if not bot_user:
        return  # não encontrou o bot, nada para renomear

    new_name = "Assistente BHZ"

    # altera usuário
    bot_user.name = new_name

    # altera partner (é o nome que aparece no chat)
    if bot_user.partner_id:
        bot_user.partner_id.name = new_name
