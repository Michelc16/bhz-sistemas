# -*- coding: utf-8 -*-
import logging
import os

_logger = logging.getLogger(__name__)

FALLBACK_STARTER_URL = "https://bhz-wa-starter.onrender.com"


def _resolve_starter_url():
    return (os.getenv("ODOO_STARTER_BASE_URL") or FALLBACK_STARTER_URL).rstrip("/")


def _resolve_webhook_secret():
    return os.getenv("ODOO_WEBHOOK_SECRET")


def _set_param(env, key, value):
    env["ir.config_parameter"].sudo().set_param(key, value)


def post_init_set_starter_defaults(cr, registry):
    """Executa na instalação do módulo: grava URL/secret."""
    from odoo.api import Environment

    env = Environment(cr, 1, {})
    base_url = _resolve_starter_url()
    _set_param(env, "starter_service.base_url", base_url)
    _logger.info("[bhz_whatsapp_omni] starter_service.base_url => %s", base_url)

    secret = _resolve_webhook_secret()
    if secret:
        _set_param(env, "starter_service.secret", secret)
        _logger.info("[bhz_whatsapp_omni] starter_service.secret configurado")
