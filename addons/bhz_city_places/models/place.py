# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzPlaceCategory(models.Model):
    _name = "bhz.place.category"
    _description = "Categoria de Local"
    _order = "sequence, name"

    name = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class BhzPlaceTag(models.Model):
    _name = "bhz.place.tag"
    _description = "Tag do Local"
    _order = "name"

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)


class BhzPlaceCity(models.Model):
    _name = "bhz.place.city"
    _description = "Cidade"
    _order = "name"

    name = fields.Char(required=True, index=True)
    state_id = fields.Many2one("res.country.state", string="Estado")
    country_id = fields.Many2one("res.country", string="País", default=lambda self: self.env.ref("base.br"))
    active = fields.Boolean(default=True)


class BhzPlace(models.Model):
    _name = "bhz.place"
    _description = "Local"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "name"

    # Organização / controle
    name = fields.Char(required=True, tracking=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        index=True,
    )
    website_id = fields.Many2one(
        "website",
        string="Website",
        help="Se definido, o local aparece apenas neste website (multi-site).",
        index=True,
    )

    # Publicação no site
    website_published = fields.Boolean(string="Publicado no Website", default=False, tracking=True)
    website_url = fields.Char(string="URL no Website", compute="_compute_website_url", store=False)

    # Classificação
    category_id = fields.Many2one("bhz.place.category", string="Categoria", index=True, tracking=True)
    tag_ids = fields.Many2many("bhz.place.tag", string="Tags")

    city_id = fields.Many2one("bhz.place.city", string="Cidade", index=True)
    neighborhood = fields.Char(string="Bairro")

    # Conteúdo e mídia
    short_description = fields.Char(string="Descrição curta", tracking=True)
    description_html = fields.Html(string="Descrição completa")
    image_1920 = fields.Image(string="Imagem", max_width=1920, max_height=1920)

    # Contato / endereço
    street = fields.Char(string="Rua")
    street2 = fields.Char(string="Complemento")
    zip = fields.Char(string="CEP")
    phone = fields.Char(string="Telefone")
    mobile = fields.Char(string="Celular/WhatsApp")
    email = fields.Char(string="E-mail")
    website = fields.Char(string="Site/Instagram")
    maps_url = fields.Char(string="Link do Google Maps")

    # Localização (opcional)
    latitude = fields.Float(string="Latitude", digits=(16, 8))
    longitude = fields.Float(string="Longitude", digits=(16, 8))

    # Extras úteis
    opening_hours = fields.Char(string="Horário de funcionamento")
    price_range = fields.Selection(
        [
            ("$", "$ (barato)"),
            ("$$", "$$ (médio)"),
            ("$$$", "$$$ (caro)"),
            ("$$$$", "$$$$ (premium)"),
        ],
        string="Faixa de preço",
    )

    @api.depends("id")
    def _compute_website_url(self):
        for rec in self:
            if rec.id:
                rec.website_url = f"/lugares/{rec.id}"
            else:
                rec.website_url = False
