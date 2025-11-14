from odoo import SUPERUSER_ID, api

CLIENT_ID = "dZCVzEyLat_rtRfHvNAuulhBUZBlz_6Lj_NZghlU7Qw"
CLIENT_SECRET = "wBI9y2hW604gkBpfxrTWoraU2UtVBC-BHWgVMn-XQE0"


def pre_init_set_magalu_client(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env["ir.config_parameter"].sudo()
    if not params.get_param("bhz_magalu.client_id"):
        params.set_param("bhz_magalu.client_id", CLIENT_ID, groups="base.group_system")
    if not params.get_param("bhz_magalu.client_secret"):
        params.set_param("bhz_magalu.client_secret", CLIENT_SECRET, groups="base.group_system")
