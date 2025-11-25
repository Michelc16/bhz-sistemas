from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bhz_wa_public_base = fields.Char(
        string="URL pública BHZ WhatsApp",
        config_parameter="bhz_wa.public_base",
        help="Ex: https://seu-dominio.odoo.com. Usado para montar as URLs de webhook.",
    )

    bhz_wa_starter_base_url = fields.Char(
        string="Starter Service URL",
        config_parameter="bhz_wa.starter_base_url",
        help="URL do serviço starter_service (Node). Ex: https://starter.bhz.com.br",
    )
    bhz_wa_starter_webhook_secret = fields.Char(
        string="Starter Webhook Secret",
        config_parameter="bhz_wa.starter_webhook_secret",
        help="Segredo compartilhado com o starter_service para validar o header X-Webhook-Secret.",
    )
    bhz_wa_business_verify_token = fields.Char(
        string="Business Verify Token (global)",
        config_parameter="bhz_wa.business_verify_token",
        help="Token usado pela Meta (Cloud API) no desafio do webhook. Pode ser sobrescrito por conta.",
    )
