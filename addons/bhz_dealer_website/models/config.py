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
        "website.website",
        string="Website",
        required=True,
        default=lambda self: self._default_website(),
        ondelete="cascade",
    )
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
