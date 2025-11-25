<<<<<<< HEAD
import base64
import os

=======
>>>>>>> 03b37ce4a9a7adc5e87ebf118e772d1eb2f49447
from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """
<<<<<<< HEAD
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

=======
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
>>>>>>> 03b37ce4a9a7adc5e87ebf118e772d1eb2f49447
    if not bot_user:
        bot_user = User.search([("name", "=", "OdooBot")], limit=1)

    if not bot_user:
<<<<<<< HEAD
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
=======
        return  # não encontrou o bot, nada para renomear

    new_name = "Assistente BHZ"

    # altera usuário
    bot_user.name = new_name

    # altera partner (é o nome que aparece no chat)
    if bot_user.partner_id:
        bot_user.partner_id.name = new_name
>>>>>>> 03b37ce4a9a7adc5e87ebf118e772d1eb2f49447
