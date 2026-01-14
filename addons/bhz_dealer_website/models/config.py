# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzDealerWebsiteConfig(models.Model):
    _name = "bhz.dealer.website.config"
    _description = "Configuração do site BHZ Dealer"
    _rec_name = "website_id"
    _sql_constraints = [
        ("website_unique", "unique(website_id)", "Já existe configuração para este website."),
    ]

    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        default=lambda self: self._default_website(),
        ondelete="cascade",
    )
    dealer_enabled = fields.Boolean("Ativar dealer no site", default=False)
    dealer_primary_color = fields.Char("Cor primária", default="#0d6efd")
    dealer_secondary_color = fields.Char("Cor secundária", default="#6610f2")
    reveal_phone = fields.Boolean("Exibir telefone", default=True)
    whatsapp_number = fields.Char("WhatsApp para CTA")
    cta_label = fields.Char("Texto do CTA", default="Quero atendimento")

    primary_color = fields.Char("Cor primária", default="#0d6efd")
    secondary_color = fields.Char("Cor secundária", default="#6610f2")
    hero_title = fields.Char("Título do hero", default="Encontre o próximo carro da sua garagem.")
    hero_subtitle = fields.Char(
        "Subtítulo do hero",
        default="Busque por marca, ano ou faixa de preço e veja os destaques selecionados.",
    )
    hero_bg_image = fields.Image("Imagem de fundo do hero", max_width=1920, max_height=1080)

    phone = fields.Char("Telefone")
    whatsapp = fields.Char("WhatsApp")
    address = fields.Char("Endereço")
    instagram_url = fields.Char("Instagram")

    @api.model
    def _default_website(self):
        website = self.env["website"].get_current_website()
        return website.id if website else False

    @api.model
    def get_for_website(self, website):
        website_id = website.id if website else False
        return self.search([("website_id", "=", website_id)], limit=1)

    def _get_or_create_page(self, website, url, name, view_xmlid):
        WebsitePage = self.env["website.page"].sudo()
        view = self.env.ref(view_xmlid, raise_if_not_found=False)
        if not view:
            return False
        page = WebsitePage.search(
            [("website_id", "=", website.id), ("url", "=", url)],
            limit=1,
        )
        if not page:
            page = WebsitePage.create(
                {
                    "name": name,
                    "website_id": website.id,
                    "url": url,
                    "view_id": view.id,
                    "is_published": True,
                }
            )
        else:
            page.view_id = view.id
            page.is_published = True
        return page

    def _get_or_create_menu(self, website, name, url, sequence, parent=None):
        WebsiteMenu = self.env["website.menu"].sudo()
        parent_id = parent.id if parent else website.main_menu.id
        menu = WebsiteMenu.search(
            [("website_id", "=", website.id), ("url", "=", url), ("parent_id", "=", parent_id)],
            limit=1,
        )
        if not menu:
            menu = WebsiteMenu.create(
                {
                    "name": name,
                    "url": url,
                    "website_id": website.id,
                    "sequence": sequence,
                    "parent_id": parent_id,
                }
            )
        else:
            menu.name = name
            menu.sequence = sequence
        return menu

    def _ensure_dealer_site_setup(self):
        for config in self:
            if not config.dealer_enabled or not config.website_id:
                continue
            website = config.website_id
            # Create pages for this website only
            home_page = config._get_or_create_page(website, "/", "Home", "bhz_dealer_website.template_dealer_home")
            stock_page = config._get_or_create_page(website, "/carros", "Estoque", "bhz_dealer_website.template_dealer_car_list")
            financing_page = config._get_or_create_page(
                website, "/financiamento", "Financiamento", "bhz_dealer_website.template_dealer_financing"
            )
            sell_page = config._get_or_create_page(
                website, "/venda-seu-carro", "Venda seu carro", "bhz_dealer_website.template_dealer_sell_car"
            )
            contact_page = config._get_or_create_page(
                website, "/contato", "Contato", "bhz_dealer_website.template_dealer_contact"
            )

            # Menus
            main_menu = website.main_menu
            config._get_or_create_menu(website, "Home", "/", 1, parent=main_menu)
            config._get_or_create_menu(website, "Estoque", "/carros", 10, parent=main_menu)
            config._get_or_create_menu(website, "Financiamento", "/financiamento", 20, parent=main_menu)
            config._get_or_create_menu(website, "Venda seu carro", "/venda-seu-carro", 30, parent=main_menu)
            config._get_or_create_menu(website, "Contato", "/contato", 40, parent=main_menu)

            # Prevent unused variables warnings
            _ = (home_page, stock_page, financing_page, sell_page, contact_page)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        enabled = res.filtered("dealer_enabled")
        if enabled:
            enabled._ensure_dealer_site_setup()
        return res

    def write(self, vals):
        res = super().write(vals)
        targets = self.filtered("dealer_enabled")
        if vals.get("dealer_enabled") or (not vals.get("dealer_enabled") and targets):
            targets._ensure_dealer_site_setup()
        return res
