# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import json

from odoo import fields, http
from odoo.http import request
from odoo.tools import image_data_uri


class GuiaBHWebsite(http.Controller):
    def _website(self):
        return request.website

    def _event_domain(self):
        website = self._website()
        return ['&', '|', ('website_id', '=', False), ('website_id', '=', website.id), ('website_published', '=', True)]

    def _place_domain(self):
        website = self._website()
        return ['&', '|', ('website_id', '=', False), ('website_id', '=', website.id), ('website_published', '=', True)]

    def _get_time_bounds(self, when):
        start = end = None
        if when == 'today':
            today = fields.Date.context_today(request.env.user)
            start_dt = datetime.combine(today, datetime.min.time())
            end_dt = datetime.combine(today, datetime.max.time())
            start = fields.Datetime.to_string(start_dt)
            end = fields.Datetime.to_string(end_dt)
        elif when == 'tomorrow':
            tomorrow = fields.Date.context_today(request.env.user) + timedelta(days=1)
            start_dt = datetime.combine(tomorrow, datetime.min.time())
            end_dt = datetime.combine(tomorrow, datetime.max.time())
            start = fields.Datetime.to_string(start_dt)
            end = fields.Datetime.to_string(end_dt)
        elif when == 'weekend':
            today = fields.Date.context_today(request.env.user)
            weekday = today.weekday()
            days_until_saturday = (5 - weekday) % 7
            saturday = today + timedelta(days=days_until_saturday)
            sunday = saturday + timedelta(days=1)
            start_dt = datetime.combine(saturday, datetime.min.time())
            end_dt = datetime.combine(sunday, datetime.max.time())
            start = fields.Datetime.to_string(start_dt)
            end = fields.Datetime.to_string(end_dt)
        return start, end

    @http.route(['/'], type='http', auth='public', website=True, sitemap=True)
    def home(self, **kwargs):
        Event = request.env['guiabh.event']
        Place = request.env['guiabh.place']
        featured_events = Event.search(self._event_domain() + [('is_featured', '=', True)], order='start_datetime asc', limit=6)
        upcoming_events = Event.search(self._event_domain(), order='start_datetime asc', limit=6)
        featured_places = Place.search(self._place_domain() + [('is_featured', '=', True)], order='name asc', limit=6)
        values = {
            'featured_events': featured_events,
            'upcoming_events': upcoming_events,
            'featured_places': featured_places,
        }
        return request.render('bhz_guiabh_website.guiabh_home', values)

    @http.route(['/eventos'], type='http', auth='public', website=True, sitemap=True)
    def events(self, page=1, **kwargs):
        Event = request.env['guiabh.event']
        page = int(page) if str(page).isdigit() else 1
        domain = list(self._event_domain())
        search_q = kwargs.get('q', '').strip()
        category = kwargs.get('cat')
        region = kwargs.get('reg')
        price_filter = kwargs.get('free') or kwargs.get('paid')
        when = kwargs.get('when')
        order = 'is_featured desc, start_datetime asc'
        ordering = kwargs.get('ordenar')
        if ordering == 'prox':
            order = 'start_datetime asc'
        if search_q:
            domain += ['|', '|', ('name', 'ilike', search_q), ('short_description', 'ilike', search_q), ('description_html', 'ilike', search_q)]
        if category:
            try:
                domain.append(('category_id', '=', int(category)))
            except ValueError:
                pass
        if region:
            try:
                domain.append(('region_id', '=', int(region)))
            except ValueError:
                pass
        if price_filter:
            if kwargs.get('free'):
                domain.append(('price_type', '=', 'free'))
            elif kwargs.get('paid'):
                domain.append(('price_type', '=', 'paid'))
        if when:
            start, end = self._get_time_bounds(when)
            if start and end:
                domain += [('start_datetime', '>=', start), ('start_datetime', '<=', end)]
        per_page = 9
        total = Event.search_count(domain)
        pager = request.website.pager(url='/eventos', total=total, page=page, step=per_page, scope=5, url_args=kwargs)
        events = Event.search(domain, order=order, limit=per_page, offset=pager['offset'])
        values = {
            'events': events,
            'pager': pager,
            'search_q': search_q,
            'categories': request.env['guiabh.event.category'].search([('active', '=', True)]),
            'regions': request.env['guiabh.region'].search([('active', '=', True)]),
            'current_filters': kwargs,
            'order': order,
        }
        return request.render('bhz_guiabh_website.guiabh_events', values)

    @http.route(['/eventos/<string:slug>'], type='http', auth='public', website=True, sitemap=True)
    def event_detail(self, slug, **kwargs):
        website = self._website()
        domain = ['|', ('website_id', '=', False), ('website_id', '=', website.id), ('slug', '=', slug)]
        if not request.env.user.has_group('website.group_website_publisher'):
            domain += [('website_published', '=', True)]
        event = request.env['guiabh.event'].search(domain, limit=1)
        if not event:
            return request.not_found()
        related_domain = self._event_domain() + ['|', ('category_id', '=', event.category_id.id), ('region_id', '=', event.region_id.id), ('id', '!=', event.id)]
        related_events = request.env['guiabh.event'].search(related_domain, order='start_datetime asc', limit=3)
        values = {
            'event': event,
            'related_events': related_events,
            'json': json,
        }
        return request.render('bhz_guiabh_website.guiabh_event_detail', values)

    @http.route(['/lugares'], type='http', auth='public', website=True, sitemap=True)
    def places(self, page=1, **kwargs):
        Place = request.env['guiabh.place']
        page = int(page) if str(page).isdigit() else 1
        domain = list(self._place_domain())
        search_q = kwargs.get('q', '').strip()
        place_type = kwargs.get('tipo')
        region = kwargs.get('reg')
        tags = kwargs.get('tags')
        order = 'is_featured desc, name asc'
        if kwargs.get('ordenar') == 'az':
            order = 'name asc'
        if search_q:
            domain += ['|', '|', ('name', 'ilike', search_q), ('short_description', 'ilike', search_q), ('description_html', 'ilike', search_q)]
        if place_type:
            try:
                domain.append(('place_type_id', '=', int(place_type)))
            except ValueError:
                pass
        if region:
            try:
                domain.append(('region_id', '=', int(region)))
            except ValueError:
                pass
        if tags:
            try:
                tag_ids = [int(t) for t in tags.split(',') if t]
                if tag_ids:
                    domain.append(('tags_ids', 'in', tag_ids))
            except ValueError:
                pass
        per_page = 9
        total = Place.search_count(domain)
        pager = request.website.pager(url='/lugares', total=total, page=page, step=per_page, scope=5, url_args=kwargs)
        places = Place.search(domain, order=order, limit=per_page, offset=pager['offset'])
        values = {
            'places': places,
            'pager': pager,
            'search_q': search_q,
            'place_types': request.env['guiabh.place.type'].search([('active', '=', True)]),
            'regions': request.env['guiabh.region'].search([('active', '=', True)]),
            'tags': request.env['guiabh.tag'].search([('active', '=', True)]),
            'current_filters': kwargs,
        }
        return request.render('bhz_guiabh_website.guiabh_places', values)

    @http.route(['/lugares/<string:slug>'], type='http', auth='public', website=True, sitemap=True)
    def place_detail(self, slug, **kwargs):
        website = self._website()
        domain = ['|', ('website_id', '=', False), ('website_id', '=', website.id), ('slug', '=', slug)]
        if not request.env.user.has_group('website.group_website_publisher'):
            domain += [('website_published', '=', True)]
        place = request.env['guiabh.place'].search(domain, limit=1)
        if not place:
            return request.not_found()
        related_domain = self._place_domain() + [('place_type_id', '=', place.place_type_id.id), ('id', '!=', place.id)]
        related_places = request.env['guiabh.place'].search(related_domain, order='name asc', limit=3)
        event_domain = self._event_domain() + [('venue_name', 'ilike', place.name)]
        place_events = request.env['guiabh.event'].search(event_domain, order='start_datetime asc', limit=3)
        values = {
            'place': place,
            'related_places': related_places,
            'place_events': place_events,
            'json': json,
        }
        return request.render('bhz_guiabh_website.guiabh_place_detail', values)

    @http.route('/guiabh/snippet/events', type='json', auth='public', website=True)
    def snippet_events_data(self, limit=6, category_id=None, region_id=None, free=None):
        limit = int(limit) if str(limit).isdigit() else 6
        domain = self._event_domain()
        if category_id:
            domain.append(('category_id', '=', int(category_id)))
        if region_id:
            domain.append(('region_id', '=', int(region_id)))
        if free:
            domain.append(('price_type', '=', 'free'))
        events = request.env['guiabh.event'].search(domain, order='is_featured desc, start_datetime asc', limit=limit)
        data = []
        for ev in events:
            cover = ev.cover_image and image_data_uri(ev.cover_image) or '/bhz_guiabh_website/static/src/img/placeholders/event_placeholder.svg'
            data.append({
                'name': ev.name,
                'slug': ev.slug,
                'url': ev.website_url or f"/eventos/{ev.slug}",
                'short_description': ev.short_description,
                'start_datetime': fields.Datetime.to_string(ev.start_datetime) if ev.start_datetime else '',
                'region': ev.region_id.name or '',
                'category': ev.category_id.name or '',
                'price_type': ev.price_type,
                'min_price': ev.min_price,
                'currency_symbol': ev.currency_id and ev.currency_id.symbol or '',
                'is_featured': ev.is_featured,
                'cover': cover,
            })
        return {'items': data}

    @http.route('/guiabh/snippet/places', type='json', auth='public', website=True)
    def snippet_places_data(self, limit=6, place_type_id=None, region_id=None, tags=None):
        limit = int(limit) if str(limit).isdigit() else 6
        domain = self._place_domain()
        if place_type_id:
            domain.append(('place_type_id', '=', int(place_type_id)))
        if region_id:
            domain.append(('region_id', '=', int(region_id)))
        if tags:
            try:
                tag_ids = [int(t) for t in str(tags).split(',') if t]
                if tag_ids:
                    domain.append(('tags_ids', 'in', tag_ids))
            except ValueError:
                pass
        places = request.env['guiabh.place'].search(domain, order='is_featured desc, name asc', limit=limit)
        data = []
        for pl in places:
            cover = pl.cover_image and image_data_uri(pl.cover_image) or '/bhz_guiabh_website/static/src/img/placeholders/place_placeholder.svg'
            data.append({
                'name': pl.name,
                'slug': pl.slug,
                'url': pl.website_url or f"/lugares/{pl.slug}",
                'short_description': pl.short_description,
                'region': pl.region_id.name or '',
                'type': pl.place_type_id.name or '',
                'price_range': pl.price_range or '',
                'is_featured': pl.is_featured,
                'cover': cover,
            })
        return {'items': data}

    @http.route(['/guias/fim-de-semana'], type='http', auth='public', website=True, sitemap=True)
    def weekend_guide(self, **kwargs):
        start, end = self._get_time_bounds('weekend')
        domain = self._event_domain()
        if start and end:
            domain += [('start_datetime', '>=', start), ('start_datetime', '<=', end)]
        weekend_events = request.env['guiabh.event'].search(domain, order='start_datetime asc', limit=6)
        values = {
            'weekend_events': weekend_events,
        }
        return request.render('bhz_guiabh_website.guiabh_weekend_guide', values)
