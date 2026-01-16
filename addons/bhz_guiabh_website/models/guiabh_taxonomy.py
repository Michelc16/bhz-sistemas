# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GuiaBHRegion(models.Model):
    _name = 'guiabh.region'
    _description = 'Região do GuiaBH'
    _order = 'name'

    name = fields.Char('Nome', required=True, translate=True)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one('website', string='Website', ondelete='set null')


class GuiaBHEventCategory(models.Model):
    _name = 'guiabh.event.category'
    _description = 'Categoria de Evento do GuiaBH'
    _order = 'name'

    name = fields.Char('Nome', required=True, translate=True)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one('website', string='Website', ondelete='set null')


class GuiaBHPlaceType(models.Model):
    _name = 'guiabh.place.type'
    _description = 'Tipo de Lugar do GuiaBH'
    _order = 'name'

    name = fields.Char('Nome', required=True, translate=True)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one('website', string='Website', ondelete='set null')


class GuiaBHTag(models.Model):
    _name = 'guiabh.tag'
    _description = 'Tag do GuiaBH'
    _order = 'name'

    name = fields.Char('Nome', required=True, translate=True)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one('website', string='Website', ondelete='set null')

    _table_args = (
        models.Constraint(
            "guiabh_tag_name_website_unique",
            type="unique",
            fields=["name", "website_id"],
        ),
    )
