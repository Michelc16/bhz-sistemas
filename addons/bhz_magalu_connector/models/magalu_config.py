from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

# nomes dos parâmetros globais
CLIENT_ID_PARAM = "bhz_magalu.client_id"
CLIENT_SECRET_PARAM = "bhz_magalu.client_secret"
REDIRECT_PARAM = "bhz_magalu.redirect_uri"


class BhzMagaluConfig(models.Model):
    _name = "bhz.magalu.config"
    _description = "Configuração Magalu (BHZ)"
    _rec_name = "name"
    _check_company_auto = True
    _order = "id desc"
    _sql_constraints = [
        ("unique_company", "unique(company_id)", "Cada empresa só pode ter uma configuração Magalu.")
    ]

    name = fields.Char(default="Configuração Magalu", readonly=True)
    environment = fields.Selection(
        [("production", "Produção")],
        default="production",
        string="Ambiente",
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    # só exibimos, não editamos
    client_id_display = fields.Char(string="Client ID (BHZ)", compute="_compute_display_params", readonly=True)
    redirect_uri_display = fields.Char(string="Redirect URI", compute="_compute_display_params", readonly=True)

    # tokens salvos por empresa
    access_token = fields.Char("Access Token", readonly=True)
    refresh_token = fields.Char("Refresh Token", readonly=True)
    token_expires_at = fields.Datetime("Token expira em", readonly=True)

    def _compute_display_params(self):
        ICP = self.env["ir.config_parameter"].sudo()
        client_id = ICP.get_param(CLIENT_ID_PARAM) or "PASTE_YOUR_CLIENT_ID_HERE"
        redirect_uri = ICP.get_param(REDIRECT_PARAM) or "https://bhzsistemas.com.br/magalu/oauth/callback"
        for rec in self:
            rec.client_id_display = client_id
            rec.redirect_uri_display = redirect_uri

    # grava tokens obtidos pelo controller
    def write_tokens(self, token_data):
        expires_in = token_data.get("expires_in", 3600)
        expire_dt = fields.Datetime.now() + datetime.timedelta(seconds=expires_in - 60)
        self.write({
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_expires_at": expire_dt,
        })

    def action_get_authorization_url(self):
        """Botão 'Conectar Magalu'."""
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        client_id = ICP.get_param("bhz_magalu.client_id")
        redirect_uri = ICP.get_param("bhz_magalu.redirect_uri")
        if not client_id or not redirect_uri:
            raise UserError(_("Parâmetros BHZ Magalu não configurados (client_id/redirect)."))
       
        scope = "apiin:all"
        authorize_url = (
            "https://id.magalu.com/login"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
            f"&response_type=code"
            f"&choose_tenants=true"
        )
        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "self",
        }

    def action_refresh_token(self):
        self.ensure_one()
        self.env["bhz.magalu.api"].refresh_token(self)
