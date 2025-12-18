import os

from odoo import SUPERUSER_ID
from odoo.api import Environment


def _ensure_env(env_or_cr):
    """Compat layer allowing env or (cr, registry) signature."""
    if isinstance(env_or_cr, Environment):
        if env_or_cr.uid != SUPERUSER_ID:
            return env_or_cr(env_or_cr.cr, SUPERUSER_ID, env_or_cr.context)
        return env_or_cr
    return Environment(env_or_cr, SUPERUSER_ID, {})


def post_init_set_starter_defaults(env_or_cr, registry=None):
    """
    Configura automaticamente os parâmetros do serviço Starter
    durante a instalação ou upgrade do módulo.
    """
    env = _ensure_env(env_or_cr)
    icp = env['ir.config_parameter'].sudo()

    # Lê variáveis de ambiente enviadas pelo Render
    base_url = (
        os.getenv('STARTER_BASE_URL')
        or os.getenv('RENDER_STARTER_URL')
        or os.getenv('STARTER_SERVICE_URL')
    )
    secret = (
        os.getenv('ODOO_WEBHOOK_SECRET')
        or os.getenv('STARTER_WEBHOOK_SECRET')
    )

    # Aplica valores padrão somente se existirem
    if base_url:
        icp.set_param('starter_service.base_url', base_url.rstrip('/'))

    if secret:
        icp.set_param('starter_service.secret', secret)

    Account = env['bhz.wa.account'].sudo()
    if base_url:
        Account.filtered(lambda acc: not acc.starter_base_url).write({
            'starter_base_url': base_url.rstrip('/'),
        })
    for account in Account.filtered(lambda acc: not acc.starter_secret):
        account._ensure_starter_secret()
    for account in Account.filtered(lambda acc: not acc.starter_session_id):
        account._get_starter_session_identifier()
