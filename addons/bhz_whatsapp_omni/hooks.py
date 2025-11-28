import os


def post_init_set_starter_defaults(cr, registry):
    """
    Configura automaticamente os parâmetros do serviço Starter
    durante a instalação ou upgrade do módulo.
    """
    from odoo.api import Environment

    env = Environment(cr, 1, {})
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
