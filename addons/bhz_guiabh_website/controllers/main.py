# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import json

from odoo import fields, http
from odoo.http import request


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

    def _search_common_domain(self):
        website = self._website()
        return ['&', '|', ('website_id', '=', False), ('website_id', '=', website.id), ('website_published', '=', True)]

    def _get_ads(self, position, limit=2):
        now = fields.Datetime.now()
        website = self._website()
        domain = [
            ('active', '=', True),
            ('position', '=', position),
            '|', ('website_id', '=', False), ('website_id', '=', website.id),
            '|', ('start_date', '=', False), ('start_date', '<=', now),
            '|', ('end_date', '=', False), ('end_date', '>=', now),
        ]
        return request.env['guiabh.ad'].sudo().search(domain, order='sequence, start_date desc', limit=limit)

    def _get_preferences(self):
        if request.env.user._is_public():
            return None
        website = self._website()
        return request.env['guiabh.preference'].sudo().search([
            ('user_id', '=', request.env.user.id),
            ('website_id', '=', website.id),
        ], limit=1)

    def _abs_url(self, path):
        base = request.httprequest.host_url.rstrip("/")
        return f"{base}{path}"

    def _resize(self, model, rec_id, field, width=800, height=600, placeholder=None):
        if rec_id and field:
            return f"/web/image/{model}/{rec_id}/{field}/{width}/{height}"
        return placeholder or ""

    def _render_cache(self, template, values, max_age=300):
        resp = request.render(template, values)
        if hasattr(resp, "headers"):
            resp.headers["Cache-Control"] = f"public, max-age={max_age}"
        return resp

    @http.route(['/sitemap_guia.xml'], type='http', auth='public', website=True, sitemap=False)
    def sitemap_guia(self, **kwargs):
        website = self._website()
        urls = [
            {'loc': self._abs_url('/')},
            {'loc': self._abs_url('/eventos')},
            {'loc': self._abs_url('/lugares')},
            {'loc': self._abs_url('/agenda')},
        ]
        Event = request.env['guiabh.event'].sudo()
        Place = request.env['guiabh.place'].sudo()
        events = Event.search(self._event_domain())
        places = Place.search(self._place_domain())
        for ev in events:
            urls.append({'loc': self._abs_url(f"/eventos/{ev.slug or ev.id}")})
        for pl in places:
            urls.append({'loc': self._abs_url(f"/lugares/{pl.slug or pl.id}")})

        body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls:
            body.append("<url>")
            body.append(f"<loc>{u['loc']}</loc>")
            body.append("</url>")
        body.append("</urlset>")
        return request.make_response("\n".join(body), headers=[('Content-Type', 'application/xml')])

    @http.route(['/buscar'], type='http', auth='public', website=True, sitemap=True)
    def search(self, page=1, **kwargs):
        Event = request.env['guiabh.event'].sudo()
        Place = request.env['guiabh.place'].sudo()
        website = self._website()

        def _intval(val):
            try:
                return int(val)
            except Exception:
                return None

        q = (kwargs.get('q') or '').strip()
        category = _intval(kwargs.get('cat'))
        region = _intval(kwargs.get('reg'))
        when = (kwargs.get('when') or '').strip()

        event_domain = list(self._search_common_domain())
        place_domain = list(self._search_common_domain())

        if q:
            event_domain += ['|', '|', ('name', 'ilike', q), ('short_description', 'ilike', q), ('description_html', 'ilike', q)]
            place_domain += ['|', '|', ('name', 'ilike', q), ('short_description', 'ilike', q), ('description_html', 'ilike', q)]
        if category:
            event_domain.append(('category_id', '=', category))
            place_domain.append(('place_type_id', '=', category))
        if region:
            event_domain.append(('region_id', '=', region))
            place_domain.append(('region_id', '=', region))
        if when:
            start, end = self._get_time_bounds(when) if when in ('today', 'weekend') else (None, None)
            if when == 'next7':
                today = fields.Date.context_today(request.env.user)
                start_dt = datetime.combine(today, datetime.min.time())
                end_dt = datetime.combine(today + timedelta(days=7), datetime.max.time())
                start = fields.Datetime.to_string(start_dt)
                end = fields.Datetime.to_string(end_dt)
            if start and end:
                event_domain += [('start_datetime', '>=', start), ('start_datetime', '<=', end)]

        step = 8
        try:
            page = max(1, int(page))
        except Exception:
            page = 1

        event_total = Event.search_count(event_domain)
        place_total = Place.search_count(place_domain)

        pager = request.website.pager(
            url='/buscar',
            total=event_total + place_total,
            page=page,
            step=step,
            scope=5,
            url_args={k: v for k, v in kwargs.items() if k != 'page'},
        )

        events = Event.search(event_domain, order='is_featured desc, start_datetime asc', limit=step, offset=pager['offset'])
        places = Place.search(place_domain, order='is_featured desc, name asc', limit=step, offset=pager['offset'])

        values = {
            'query': q,
            'events': events,
            'places': places,
            'pager': pager,
            'categories': request.env['guiabh.event.category'].search([('active', '=', True)]),
            'regions': request.env['guiabh.region'].search([('active', '=', True)]),
            'current_filters': kwargs,
            'website': website,
            'when': when,
        }
        return request.render('bhz_guiabh_website.guiabh_search', values)

    @http.route(['/'], type='http', auth='public', website=True, sitemap=True)
    def home(self, **kwargs):
        Event = request.env['guiabh.event']
        Place = request.env['guiabh.place']
        featured_events = Event.search(self._event_domain() + [('is_featured', '=', True)], order='start_datetime asc', limit=6)
        upcoming_events = Event.search(self._event_domain(), order='start_datetime asc', limit=6)
        featured_places = Place.search(self._place_domain() + [('is_featured', '=', True)], order='name asc', limit=6)
        prefs = self._get_preferences()
        pref_event_domain = self._event_domain()
        pref_place_domain = self._place_domain()
        if prefs:
            if prefs.category_ids:
                pref_event_domain.append(('category_id', 'in', prefs.category_ids.ids))
            if prefs.region_ids:
                pref_event_domain.append(('region_id', 'in', prefs.region_ids.ids))
                pref_place_domain.append(('region_id', 'in', prefs.region_ids.ids))
        else:
            pref_event_domain = []
            pref_place_domain = []

        pref_events = Event.search(pref_event_domain, order='start_datetime asc', limit=6) if pref_event_domain else Event.browse()
        pref_places = Place.search(pref_place_domain, order='name asc', limit=6) if pref_place_domain else Place.browse()

        values = {
            'featured_events': featured_events,
            'upcoming_events': upcoming_events,
            'featured_places': featured_places,
            'ads_home_top': self._get_ads('home_top', limit=2),
            'ads_between': self._get_ads('between_sections', limit=2),
            'pref_events': pref_events,
            'pref_places': pref_places,
            'preferences': prefs,
        }
        return self._render_cache('bhz_guiabh_website.guiabh_home', values)

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
        ordering = kwargs.get('ordenar')
        order = 'is_featured desc, start_datetime asc'
        if ordering == 'date':
            order = 'start_datetime asc'
        elif ordering == 'recent':
            order = 'create_date desc'
        elif ordering == 'featured':
            order = 'is_featured desc, start_datetime asc'
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
            'ordering': ordering or 'featured',
            'ads_sidebar': self._get_ads('sidebar', limit=1),
        }
        return self._render_cache('bhz_guiabh_website.guiabh_events', values, max_age=120)

    @http.route(['/eventos/<string:slug>', '/evento/<string:slug>'], type='http', auth='public', website=True, sitemap=True)
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
            'share_url': request.httprequest.url,
        }
        return self._render_cache('bhz_guiabh_website.guiabh_event_detail', values, max_age=120)

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
        elif kwargs.get('ordenar') == 'recent':
            order = 'create_date desc'
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
            'ads_sidebar': self._get_ads('sidebar', limit=1),
        }
        return self._render_cache('bhz_guiabh_website.guiabh_places', values, max_age=120)

    @http.route(['/agenda'], type='http', auth='public', website=True, sitemap=True)
    def agenda(self, view='week', cat=None, reg=None, **kwargs):
        Event = request.env['guiabh.event']
        today = fields.Date.context_today(request.env.user)

        # Define interval
        if view == 'month':
            start_date = today.replace(day=1)
            # next month first day
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1, day=1)
            end_date = next_month - timedelta(days=1)
        else:
            # week view (Monday-Sunday)
            weekday = today.weekday()
            start_date = today - timedelta(days=weekday)
            end_date = start_date + timedelta(days=6)

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        start_str = fields.Datetime.to_string(start_dt)
        end_str = fields.Datetime.to_string(end_dt)

        domain = list(self._event_domain())
        domain += [('start_datetime', '>=', start_str), ('start_datetime', '<=', end_str)]

        try:
            cat_id = int(cat) if cat else None
        except Exception:
            cat_id = None
        try:
            reg_id = int(reg) if reg else None
        except Exception:
            reg_id = None

        if cat_id:
            domain.append(('category_id', '=', cat_id))
        if reg_id:
            domain.append(('region_id', '=', reg_id))

        events = Event.search(domain, order='start_datetime asc, is_featured desc')

        # Group by date
        grouped = {}
        for ev in events:
            day = fields.Date.to_date(ev.start_datetime)
            grouped.setdefault(day, []).append(ev)
        sorted_days = sorted(grouped.keys())
        day_blocks = [(day, grouped[day]) for day in sorted_days]

        values = {
            'view_mode': view,
            'start_date': start_date,
            'end_date': end_date,
            'today': today,
            'day_blocks': day_blocks,
            'categories': request.env['guiabh.event.category'].search([('active', '=', True)]),
            'regions': request.env['guiabh.region'].search([('active', '=', True)]),
            'current_filters': {'cat': cat, 'reg': reg},
        }
        return self._render_cache('bhz_guiabh_website.guiabh_agenda', values, max_age=120)

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
        return self._render_cache('bhz_guiabh_website.guiabh_place_detail', values, max_age=120)

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
            cover = ev.cover_image and f"/web/image/guiabh.event/{ev.id}/cover_image" or '/bhz_guiabh_website/static/src/img/placeholders/event_placeholder.svg'
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
            cover = pl.cover_image and f"/web/image/guiabh.place/{pl.id}/cover_image" or '/bhz_guiabh_website/static/src/img/placeholders/place_placeholder.svg'
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

    @http.route(['/favoritos/toggle'], type='http', auth='user', website=True)
    def favorite_toggle(self, model=None, res_id=None, redirect=None, **kwargs):
        allowed_models = {"guiabh.event", "guiabh.place"}
        if model not in allowed_models or not res_id:
            return request.redirect(redirect or '/minha-lista')
        try:
            res_id = int(res_id)
        except Exception:
            return request.redirect(redirect or '/minha-lista')
        website = self._website()
        record = request.env[model].sudo().browse(res_id)
        if not record.exists():
            return request.redirect(redirect or '/minha-lista')
        if record.website_id and record.website_id.id != website.id:
            return request.redirect(redirect or '/minha-lista')
        if hasattr(record, "website_published") and not record.website_published:
            return request.redirect(redirect or '/minha-lista')

        Fav = request.env['guiabh.favorite'].sudo()
        fav = Fav.search([
            ('user_id', '=', request.env.user.id),
            ('website_id', '=', website.id),
            ('res_model', '=', model),
            ('res_id', '=', res_id),
        ], limit=1)
        if fav:
            fav.unlink()
        else:
            Fav.create({
                'user_id': request.env.user.id,
                'website_id': website.id,
                'res_model': model,
                'res_id': res_id,
            })
        return request.redirect(redirect or request.httprequest.referrer or '/minha-lista')

    @http.route(['/minha-lista'], type='http', auth='user', website=True, sitemap=False)
    def favorites(self, **kwargs):
        website = self._website()
        Fav = request.env['guiabh.favorite'].sudo()
        favs = Fav.search([('user_id', '=', request.env.user.id), ('website_id', '=', website.id)])
        event_ids = favs.filtered(lambda f: f.res_model == "guiabh.event").mapped('res_id')
        place_ids = favs.filtered(lambda f: f.res_model == "guiabh.place").mapped('res_id')
        events = request.env['guiabh.event'].sudo().browse(event_ids).exists()
        places = request.env['guiabh.place'].sudo().browse(place_ids).exists()
        values = {
            'events': events,
            'places': places,
        }
        return request.render('bhz_guiabh_website.guiabh_favorites', values)

    @http.route(['/preferencias/salvar'], type='http', auth='user', website=True, methods=['POST'])
    def preferences_save(self, **kwargs):
        prefs = self._get_preferences()
        category_ids = kwargs.getlist('categories') if hasattr(kwargs, 'getlist') else kwargs.get('categories', [])
        region_ids = kwargs.getlist('regions') if hasattr(kwargs, 'getlist') else kwargs.get('regions', [])
        try:
            cat_ids = [int(c) for c in category_ids if c]
        except Exception:
            cat_ids = []
        try:
            reg_ids = [int(r) for r in region_ids if r]
        except Exception:
            reg_ids = []

        vals = {
            'user_id': request.env.user.id,
            'website_id': request.website.id,
            'category_ids': [(6, 0, cat_ids)],
            'region_ids': [(6, 0, reg_ids)],
        }
        if prefs:
            prefs.write(vals)
        else:
            request.env['guiabh.preference'].sudo().create(vals)
        return request.redirect(request.httprequest.referrer or '/')

    @http.route(['/lead/guiabh'], type='http', auth='public', website=True, methods=['POST'])
    def lead_submit(self, **kwargs):
        name = (kwargs.get('name') or '').strip()
        email = (kwargs.get('email') or '').strip()
        categories = kwargs.getlist('categories') if hasattr(kwargs, 'getlist') else kwargs.get('categories', [])
        consent = kwargs.get('consent') == 'on'

        if not name or not email:
            return request.redirect('/obrigado?error=missing')

        try:
            category_ids = [int(c) for c in categories if c]
        except Exception:
            category_ids = []

        vals = {
            'name': name,
            'email': email,
            'consent_lgpd': consent,
            'website_id': request.website.id,
        }
        if category_ids:
            vals['category_ids'] = [(6, 0, category_ids)]
        request.env['guiabh.lead'].sudo().create(vals)
        return request.redirect('/obrigado')

    @http.route(['/obrigado'], type='http', auth='public', website=True, sitemap=True)
    def thank_you(self, **kwargs):
        return request.render('bhz_guiabh_website.guiabh_thanks', {'error': kwargs.get('error')})
