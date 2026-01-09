# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import slugify


class GuiaBHEvent(models.Model):
    _name = 'guiabh.event'
    _description = 'Evento do GuiaBH'
    _inherit = ['website.published.mixin']
    _order = 'is_featured desc, start_datetime asc, name'

    name = fields.Char('Nome', required=True, translate=True)
    slug = fields.Char('Slug', compute='_compute_slug', store=True, readonly=False, index=True)
    active = fields.Boolean(default=True)
    cover_image = fields.Image('Imagem de capa')
    short_description = fields.Char('Resumo', translate=True)
    description_html = fields.Html('Descrição detalhada', sanitize=True)
    start_datetime = fields.Datetime('Início', required=True)
    end_datetime = fields.Datetime('Fim')
    venue_name = fields.Char('Local do evento')
    address_text = fields.Char('Endereço')
    region_id = fields.Many2one('guiabh.region', string='Região')
    category_id = fields.Many2one('guiabh.event.category', string='Categoria')
    tags_ids = fields.Many2many('guiabh.tag', string='Tags')
    price_type = fields.Selection([
        ('free', 'Gratuito'),
        ('paid', 'Pago'),
    ], string='Tipo de preço', default='free', required=True)
    min_price = fields.Monetary('Preço mínimo', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moeda', default=lambda self: self.env.company.currency_id.id, required=True)
    ticket_url = fields.Char('Link para ingresso')
    is_featured = fields.Boolean('Em destaque', default=False)
    published = fields.Boolean('Publicado internamente', default=True)
    website_id = fields.Many2one('website', string='Website', ondelete='set null', default=lambda self: self.env['website'].get_current_website())

    _sql_constraints = [
        ('slug_website_unique', 'unique(slug, website_id)', 'O slug deve ser único por website.'),
    ]

    @api.depends('name', 'website_id')
    def _compute_slug(self):
        for record in self:
            base_value = record.slug or record.name
            base_slug = slugify(base_value) or 'item'
            candidate = base_slug
            suffix = 1
            domain = [('id', '!=', record.id), ('website_id', '=', record.website_id.id if record.website_id else False)]
            while record.search_count([('slug', '=', candidate)] + domain):
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
            record.slug = candidate

    def _compute_website_url(self):
        super()._compute_website_url()
        for record in self:
            if record.slug:
                record.website_url = f"/eventos/{record.slug}"

    def action_publish(self):
        self.write({'website_published': True})

    def action_unpublish(self):
        self.write({'website_published': False})
