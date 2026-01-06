# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzPlaceCategory(models.Model):
    _name = "bhz.place.category"
    _description = "Categoria de Local"
    _order = "sequence, name"

    name = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        index=True,
    )


class BhzPlaceTag(models.Model):
    _name = "bhz.place.tag"
    _description = "Tag do Local"
    _order = "name"

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        index=True,
    )


class BhzPlaceCity(models.Model):
    _name = "bhz.place.city"
    _description = "Cidade"
    _order = "name"

    name = fields.Char(required=True, index=True)
    state_id = fields.Many2one("res.country.state", string="Estado")
    country_id = fields.Many2one("res.country", string="País", default=lambda self: self.env.ref("base.br"))
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        index=True,
    )


class BhzPlaceStage(models.Model):
    _name = "bhz.place.stage"
    _description = "Etapa do Local"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=False)
    sequence = fields.Integer(default=10)
    is_published_stage = fields.Boolean(
        string="Publicar nesta etapa",
        help="Quando ativo, os locais nesta etapa serão publicados automaticamente no site.",
    )
    fold = fields.Boolean(string="Recolher no kanban", default=False)
    color = fields.Integer(string="Cor")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        index=True,
    )


class BhzPlace(models.Model):
    _name = "bhz.place"
    _description = "Local"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "name"

    _check_company_auto = True

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
    stage_id = fields.Many2one(
        "bhz.place.stage",
        string="Etapa",
        tracking=True,
        copy=False,
        index=True,
        default=lambda self: self._default_stage_id(),
    )

    # Classificação
    category_id = fields.Many2one("bhz.place.category", string="Categoria", index=True, tracking=True)
    tag_ids = fields.Many2many("bhz.place.tag", string="Tags")

    city_id = fields.Many2one("bhz.place.city", string="Cidade", index=True)
    neighborhood = fields.Char(string="Bairro")

    # Conteúdo e mídia
    short_description = fields.Html(
        string="Descrição curta",
        sanitize=True,
        translate=False,
        tracking=True,
        help="Texto breve usado em destaques. Permite formatação básica para ajustar a estrutura.",
    )
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

    def action_open_website(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/lugares/{self.id}",
            "target": "self",
        }

    @api.model
    def _default_stage_id(self):
        return self.env.ref("bhz_city_places.stage_bhz_place_draft", raise_if_not_found=False)

    @api.model_create_multi
    def create(self, vals_list):
        default_stage = self._default_stage_id()
        for vals in vals_list:
            if not vals.get("stage_id") and default_stage:
                vals["stage_id"] = default_stage.id
            stage = None
            stage_id = vals.get("stage_id")
            if stage_id:
                stage = self.env["bhz.place.stage"].browse(stage_id)
            if stage and "website_published" not in vals:
                vals["website_published"] = stage.is_published_stage
        records = super().create(vals_list)
        return records

    def write(self, vals):
        res = super().write(vals)
        if "stage_id" in vals and "website_published" not in vals:
            for record in self:
                if record.stage_id:
                    record.website_published = record.stage_id.is_published_stage
        return res
