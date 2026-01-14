# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
class BhzDealerCar(models.Model):
    _name = "bhz.dealer.car"
    _description = "Carro - Concessionária"
    _inherit = ["mail.thread", "mail.activity.mixin", "website.published.mixin"]
    _order = "is_featured desc, create_date desc"

    name = fields.Char(string="Título do anúncio", required=True, tracking=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, index=True)
    website_id = fields.Many2one(
        "website",
        string="Website",
        index=True,
        default=lambda self: self._get_fallback_website_id(),
        help="Se vazio, aparece em qualquer website.",
    )

    # Identificação
    brand = fields.Char("Marca", required=True, index=True)
    model = fields.Char("Modelo", required=True, index=True)
    trim = fields.Char("Versão")
    year = fields.Integer("Ano", required=True, index=True)
    color = fields.Char("Cor")
    plate_final = fields.Char("Final da placa")

    # Dados comerciais
    price = fields.Monetary("Preço", currency_field="currency_id", required=True, tracking=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    mileage_km = fields.Integer("KM", default=0)
    fuel = fields.Selection([
        ("gasoline", "Gasolina"),
        ("ethanol", "Etanol"),
        ("flex", "Flex"),
        ("diesel", "Diesel"),
        ("hybrid", "Híbrido"),
        ("electric", "Elétrico"),
    ], string="Combustível", default="flex", index=True)
    transmission = fields.Selection([
        ("manual", "Manual"),
        ("auto", "Automático"),
        ("cvt", "CVT"),
    ], string="Câmbio", default="auto", index=True)

    doors = fields.Integer("Portas", default=4)
    condition = fields.Selection([
        ("new", "Novo"),
        ("used", "Usado"),
        ("seminovo", "Seminovo"),
    ], string="Condição", default="seminovo", index=True)

    # Conteúdo
    description = fields.Html("Descrição")
    features = fields.Text("Opcionais (1 por linha)")
    optional_lines = fields.Text("Itens opcionais", related="features", readonly=False)
    main_image = fields.Image("Imagem principal", max_width=1920, max_height=1080)
    image_ids = fields.One2many("bhz.dealer.car.image", "car_id", string="Galeria")

    is_featured = fields.Boolean("Destaque", default=False, index=True)
    owners_count = fields.Integer("Nº de donos", default=1)
    slug = fields.Char("Slug (URL)", compute="_compute_slug", store=True, index=True)
    website_url = fields.Char("Website URL", compute="_compute_website_url", help="URL pública deste carro.")

    # Contato / CTA
    whatsapp = fields.Char("WhatsApp do anúncio", help="Ex: 5531999999999 (sem + e sem espaços)")
    lead_email_to = fields.Char("E-mail de leads (opcional)")

    @api.depends("brand", "model", "year", "name")
    def _compute_slug(self):
        for rec in self:
            base = (rec.name or f"{rec.brand} {rec.model} {rec.year}").strip().lower()
            rec.slug = base.replace(" ", "-").replace("/", "-")

    @api.constrains("year")
    def _check_year(self):
        for rec in self:
            if rec.year and (rec.year < 1950 or rec.year > 2100):
                raise ValidationError("Ano inválido.")

    def _compute_website_url(self):
        super()._compute_website_url()
        for rec in self:
            slug = rec.slug or (rec.name or "").replace(" ", "-")
            rec.website_url = f"/carros/{rec.id}-{slug}"

    @api.model
    def _get_fallback_website_id(self):
        website = self.env["website"].get_current_website()
        return website.id if website else False

    @api.model
    def create(self, vals):
        fallback = self._get_fallback_website_id()

        def _inject(valdict):
            data = dict(valdict or {})
            if not data.get("website_id") and fallback:
                data["website_id"] = fallback
            return data

        if isinstance(vals, list):
            prepared = [_inject(v) for v in vals]
            return super().create(prepared)

        vals = _inject(vals)
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        if not vals.get("website_id"):
            fallback = self._get_fallback_website_id()
            if fallback:
                no_site = self.filtered(lambda rec: not rec.website_id)
                if no_site:
                    super(BhzDealerCar, no_site).write({"website_id": fallback})
        return res

    def action_view_on_website(self):
        self.ensure_one()
        website = self.website_id or self.env["website"].get_current_website()
        base = website.get_base_url() if website else self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        url = f"{base}{self.website_url or '/carros'}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

class BhzDealerCarImage(models.Model):
    _name = "bhz.dealer.car.image"
    _description = "Imagem do carro"
    _order = "sequence, id"

    car_id = fields.Many2one("bhz.dealer.car", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char("Legenda")
    image = fields.Image("Imagem", required=True, max_width=1920, max_height=1080)
