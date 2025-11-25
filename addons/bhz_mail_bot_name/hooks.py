from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Renomeia o OdooBot para Assistente BHZ após instalar o módulo."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    User = env["res.users"].sudo()

    # Tenta pegar pelo xml_id (mais comum nas versões recentes)
    bot_user = env.ref("mail_bot.user_odoobot", raise_if_not_found=False)

    # Se não achar pelo xml_id, procura pelo login ou nome
    if not bot_user:
        bot_user = User.search(
            [("login", "=", "odoobot")],
            limit=1,
        )

    if not bot_user:
        bot_user = User.search(
            [("name", "=", "OdooBot")],
            limit=1,
        )

    if not bot_user:
        # Se não encontrou nada, não faz nada
        return

    new_name = "Assistente BHZ"

    # Altera o nome do usuário
    bot_user.name = new_name

    # Altera também o nome do partner vinculado (é o que aparece no chat)
    if bot_user.partner_id:
        bot_user.partner_id.name = new_name