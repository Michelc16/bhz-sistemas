# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class GuiaBHPlace(models.Model):
    _name = 'guiabh.place'
    _description = 'Lugar do GuiaBH'
    _inherit = ['website.published.mixin']
    _order = 'is_featured desc, name'

    name = fields.Char('Nome', required=True, translate=True)
    slug = fields.Char('Slug', compute='_compute_slug', store=True, readonly=False, index=True)
    active = fields.Boolean(default=True)
    cover_image = fields.Image('Imagem de capa')
    gallery_image_ids = fields.Many2many(
        'ir.attachment',
        'guiabh_place_gallery_rel',
        'place_id',
        'attachment_id',
        string='Galeria de imagens',
    )
    short_description = fields.Char('Resumo', translate=True)
    description_html = fields.Html('Descrição detalhada', sanitize=True)
    place_type_id = fields.Many2one('guiabh.place.type', string='Tipo de lugar')
    tags_ids = fields.Many2many('guiabh.tag', string='Tags')
    region_id = fields.Many2one('guiabh.region', string='Região')
    address_text = fields.Char('Endereço')
    phone = fields.Char('Telefone/WhatsApp')
    instagram = fields.Char('Instagram')
    website_link = fields.Char('Site oficial')
    opening_hours = fields.Char('Horário de funcionamento')
    price_range = fields.Selection([
        ('$', '$ (economia)'),
        ('$$', '$$ (médio)'),
        ('$$$', '$$$ (premium)'),
    ], string='Faixa de preço')
    is_featured = fields.Boolean('Em destaque', default=False)
    website_id = fields.Many2one('website', string='Website', ondelete='set null', default=lambda self: self.env['website'].get_current_website())

    _sql_constraints = [
        ('place_slug_website_unique', 'unique(slug, website_id)', 'O slug deve ser único por website.'),
    ]

    @api.depends('name', 'website_id')
    def _compute_slug(self):
        for record in self:
            base_value = (record.slug or record.name or '').strip()
            base_slug = self._simple_slugify(base_value) or 'lugar'
            candidate = base_slug
            suffix = 1
            domain = [('id', '!=', record.id), ('website_id', '=', record.website_id.id if record.website_id else False)]
            while record.search_count([('slug', '=', candidate)] + domain):
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
            record.slug = candidate

    @staticmethod
    def _simple_slugify(value):
        value = (value or '').lower()
        value = re.sub(r'[^a-z0-9]+', '-', value, flags=re.IGNORECASE)
        value = re.sub(r'-+', '-', value).strip('-')
        return value

    def _compute_website_url(self):
        super()._compute_website_url()
        for record in self:
            if record.slug:
                record.website_url = f"/lugares/{record.slug}"

    def action_publish(self):
        self.write({'website_published': True})

    def action_unpublish(self):
        self.write({'website_published': False})
