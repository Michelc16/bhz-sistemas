import secrets

from odoo import SUPERUSER_ID, api

CLIENT_ID = "djlPMQL1CrD1kv7A4qBvSSaIkHmiZFJ81EVflZpnCdY"
CLIENT_SECRET = "C4xlUMsKpMINRduPjhMvznuUdi0JWjQHSO0QcdSxGtM"
DEFAULT_SCOPE_STRING = "openid open:order-order-seller:read open:order-delivery-seller:read open:order-invoice-seller:read open:portfolio-skus-seller:read open:portfolio-stocks-seller:read"


def pre_init_set_magalu_client(env_or_cr):
    """Hook executado antes da instalação do módulo."""
    if isinstance(env_or_cr, api.Environment):
        env = env_or_cr
    else:
        cr = env_or_cr
        env = api.Environment(cr, SUPERUSER_ID, {})

    params = env["ir.config_parameter"].sudo()

    def ensure_param(key, value):
        if not params.get_param(key):
            params.set_param(key, value)

    ensure_param("bhz_magalu.client_id", CLIENT_ID)
    ensure_param("bhz_magalu.client_secret", CLIENT_SECRET)
    ensure_param("bhz_magalu.oauth_scopes", DEFAULT_SCOPE_STRING)
    ensure_param("bhz_magalu.allowed_scopes", "")
    ensure_param("bhz_magalu.state_secret", secrets.token_hex(32))
