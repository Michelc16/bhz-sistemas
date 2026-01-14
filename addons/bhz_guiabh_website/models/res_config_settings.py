# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    guiabh_create_site = fields.Boolean(
        string="Criar site GuiaBH",
        help="Cria um novo website para o GuiaBH sem alterar sites existentes.")
    guiabh_site_name = fields.Char(
        string="Nome do site GuiaBH",
        default="GuiaBH",
        help="Nome do novo website a ser criado.")
    guiabh_apply_theme = fields.Boolean(
        string="Aplicar tema GuiaBH no novo site",
        help="Aplica o tema do GuiaBH apenas no website criado/selecionado.")

    guiabh_home_limit_featured_events = fields.Integer(
        string="Qtde Eventos em Destaque",
        default=8,
        help="Número de eventos em destaque exibidos na home GuiaBH.")
    guiabh_home_limit_upcoming_events = fields.Integer(
        string="Qtde Próximos Eventos",
        default=8,
        help="Número de próximos eventos exibidos na home GuiaBH.")
    guiabh_home_limit_movies = fields.Integer(
        string="Qtde Filmes",
        default=8,
        help="Número de filmes em cartaz/estreias exibidos na home GuiaBH.")
    guiabh_home_limit_matches = fields.Integer(
        string="Qtde Jogos",
        default=6,
        help="Número de jogos exibidos na home GuiaBH.")
    guiabh_home_limit_places = fields.Integer(
        string="Qtde Lugares",
        default=8,
        help="Número de lugares exibidos na home GuiaBH.")
    guiabh_home_limit_banners = fields.Integer(
        string="Qtde Banners",
        default=5,
        help="Número de banners do carrossel exibidos na home GuiaBH.")

    def execute(self):
        res = super().execute()
        for config in self:
            if config.guiabh_create_site:
                config._create_guiabh_site(apply_theme=config.guiabh_apply_theme)
        return res

    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update({
            'guiabh_home_limit_featured_events': int(ICP.get_param('bhz_guiabh_website.home_limit_featured_events', default=8)),
            'guiabh_home_limit_upcoming_events': int(ICP.get_param('bhz_guiabh_website.home_limit_upcoming_events', default=8)),
            'guiabh_home_limit_movies': int(ICP.get_param('bhz_guiabh_website.home_limit_movies', default=8)),
            'guiabh_home_limit_matches': int(ICP.get_param('bhz_guiabh_website.home_limit_matches', default=6)),
            'guiabh_home_limit_places': int(ICP.get_param('bhz_guiabh_website.home_limit_places', default=8)),
            'guiabh_home_limit_banners': int(ICP.get_param('bhz_guiabh_website.home_limit_banners', default=5)),
        })
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('bhz_guiabh_website.home_limit_featured_events', self.guiabh_home_limit_featured_events or 8)
        ICP.set_param('bhz_guiabh_website.home_limit_upcoming_events', self.guiabh_home_limit_upcoming_events or 8)
        ICP.set_param('bhz_guiabh_website.home_limit_movies', self.guiabh_home_limit_movies or 8)
        ICP.set_param('bhz_guiabh_website.home_limit_matches', self.guiabh_home_limit_matches or 6)
        ICP.set_param('bhz_guiabh_website.home_limit_places', self.guiabh_home_limit_places or 8)
        ICP.set_param('bhz_guiabh_website.home_limit_banners', self.guiabh_home_limit_banners or 5)

    def _get_guiabh_theme_module(self):
        theme_module = self.env['ir.module.module'].sudo().search([('name', '=', 'bhz_guiabh_website')], limit=1)
        if not theme_module or theme_module.state != 'installed':
            raise UserError(_("O tema bhz_guiabh_website precisa estar instalado para ser aplicado."))
        return theme_module

    def _create_guiabh_site(self, apply_theme=False):
        Website = self.env['website'].sudo()
        name = self.guiabh_site_name or "GuiaBH"
        website = Website.create({
            'name': name,
            'company_id': self.env.company.id,
            'user_id': self.env.ref('base.public_user').id,
        })

        if apply_theme:
            theme_module = self._get_guiabh_theme_module()
            # Apply theme only to the new website, with explicit context to avoid touching others.
            website.with_context(website_id=website.id, apply_new_theme=True).theme_id = theme_module

        return website
