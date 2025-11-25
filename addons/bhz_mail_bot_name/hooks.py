import base64
import os

from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """
    Executado após instalar o módulo.

    - renomeia o OdooBot para Assistente BHZ
    - troca avatar do parceiro do bot pela logo BHZ
    """

    # recria um Environment completo com superusuário
    real_env = api.Environment(env.cr, SUPERUSER_ID, {})
    User = real_env["res.users"]

    # tenta localizar o usuário do bot
    bot_user = real_env.ref("mail_bot.user_odoobot", raise_if_not_found=False)

    if not bot_user:
        bot_user = User.search([("login", "=", "odoobot")], limit=1)

    if not bot_user:
        bot_user = User.search([("name", "=", "OdooBot")], limit=1)

    if not bot_user:
        return  # não achou o bot, nada para fazer

    new_name = "Assistente BHZ"

    # renomeia usuário e partner
    bot_user.name = new_name
    if bot_user.partner_id:
        bot_user.partner_id.name = new_name

        # aplica avatar personalizado
        # caminho relativo à pasta do módulo
        module_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(
            module_path,
            "static",
            "src",
            "img",
            "bhz_assistente_avatar.png",
        )

        if os.path.isfile(img_path):
            with open(img_path, "rb") as f:
                img_data = f.read()
            bot_user.partner_id.image_1920 = base64.b64encode(img_data)
