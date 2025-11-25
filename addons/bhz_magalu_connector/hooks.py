from odoo import SUPERUSER_ID, api

CLIENT_ID = "dZCVzEyLat_rtRfHvNAuulhBUZBlz_6Lj_NZghlU7Qw"
CLIENT_SECRET = "wBI9y2hW604gkBpfxrTWoraU2UtVBC-BHWgVMn-XQE0"


<<<<<<< HEAD
def pre_init_set_magalu_client(env_or_cr):
    """Hook executado antes da instalação do módulo.

    Em Odoo 19, o hook está sendo chamado com um Environment.
    Este código também trata o caso de vir um cursor (cr).
    """
    if isinstance(env_or_cr, api.Environment):
        # Caso do Odoo 19: já vem um Environment pronto
        env = env_or_cr
    else:
        # Caso antigo: vem o cursor cr
        cr = env_or_cr
        env = api.Environment(cr, SUPERUSER_ID, {})

    params = env["ir.config_parameter"].sudo()

    # Não usar 'groups' em Odoo 19.0, apenas chave e valor
    if not params.get_param("bhz_magalu.client_id"):
        params.set_param("bhz_magalu.client_id", CLIENT_ID)

    if not params.get_param("bhz_magalu.client_secret"):
        params.set_param("bhz_magalu.client_secret", CLIENT_SECRET)
=======
def pre_init_set_magalu_client(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env["ir.config_parameter"].sudo()
    if not params.get_param("bhz_magalu.client_id"):
        params.set_param("bhz_magalu.client_id", CLIENT_ID, groups="base.group_system")
    if not params.get_param("bhz_magalu.client_secret"):
        params.set_param("bhz_magalu.client_secret", CLIENT_SECRET, groups="base.group_system")
>>>>>>> 03b37ce4a9a7adc5e87ebf118e772d1eb2f49447
