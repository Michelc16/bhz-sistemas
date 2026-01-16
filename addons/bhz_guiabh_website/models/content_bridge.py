# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class GuiaBHContentBridge(models.AbstractModel):
    _name = "bhz.guiabh.content.bridge"
    _description = "Serviço de conteúdo integrado (GuiaBH)"

    # Helpers -------------------------------------------------------------
    def _get_model(self, model_name):
        """Restricted getter for models available in this database."""
        try:
            return self.env[model_name].sudo()
        except KeyError:
            return None

    def _module_installed(self, module_name):
        module = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", module_name), ("state", "=", "installed")], limit=1)
        )
        return bool(module)

    def _website_domain(self, Model, website):
        # Show only records from this module regardless of website context.
        return []

    def _company_domain(self, Model, website):
        domain = []
        company = website.company_id if website else False
        if company and "company_id" in Model._fields:
            domain = [("company_id", "in", [False, company.id])]
        return domain

    def _published_domain(self, Model):
        domain = []
        if "website_published" in Model._fields:
            domain.append(("website_published", "=", True))
        if "active" in Model._fields:
            domain.append(("active", "=", True))
        if "show_on_public_agenda" in Model._fields:
            domain.append(("show_on_public_agenda", "=", True))
        return domain

    def _image_url(self, record, field_name, width=1200, height=700, placeholder=""):
        if record and hasattr(record, "_fields") and field_name in record._fields and record[field_name]:
            return f"/web/image/{record._name}/{record.id}/{field_name}/{width}/{height}"
        return placeholder

    def _placeholder(self, kind):
        if kind == "event":
            return "/bhz_guiabh_website/static/src/img/placeholders/event_placeholder.svg"
        if kind == "place":
            return "/bhz_guiabh_website/static/src/img/placeholders/place_placeholder.svg"
        return "/bhz_guiabh_website/static/src/img/placeholders/editorial_placeholder.svg"

    def _format_datetime(self, dt):
        if not dt:
            return ""
        user = self.env.user
        tz_user = user.with_context(tz=user.tz or self.env.context.get("tz") or "UTC")
        local_dt = fields.Datetime.context_timestamp(tz_user, dt)
        return local_dt.strftime("%d/%m/%Y %H:%M")

    # Public API ----------------------------------------------------------
    @api.model
    def get_featured_events(self, limit=6, website=None):
        website = website or self.env["website"].get_current_website()
        Event = self._get_model("guiabh.event")
        if not Event:
            return []
        domain = [
            ("website_published", "=", True),
            ("active", "=", True),
        ] + self._website_domain(Event, website)
        events = Event.search(domain, order="is_featured desc, start_datetime asc, id desc", limit=limit)
        return [self._serialize_event(ev, website) for ev in events]

    @api.model
    def get_upcoming_events(self, limit=6, date_window=30, website=None):
        website = website or self.env["website"].get_current_website()
        Event = self._get_model("guiabh.event")
        if not Event:
            return []
        now = fields.Datetime.now()
        end = now + timedelta(days=date_window or 30)
        domain = [
            ("website_published", "=", True),
            ("active", "=", True),
        ] + self._website_domain(Event, website)
        if "start_datetime" in Event._fields:
            domain += [("start_datetime", ">=", now), ("start_datetime", "<=", end)]
        events = Event.search(domain, order="start_datetime asc, id desc", limit=limit)
        if not events:
            events = Event.search(
                [("website_published", "=", True), ("active", "=", True)],
                order="start_datetime desc, id desc",
                limit=limit,
            )
        return [self._serialize_event(ev, website) for ev in events]

    @api.model
    def get_featured_places(self, limit=6, website=None):
        website = website or self.env["website"].get_current_website()
        Place = self._get_model("guiabh.place")
        if not Place:
            return []
        domain = [
            ("active", "=", True),
            ("website_published", "=", True),
            ("is_featured", "=", True),
        ] + self._website_domain(Place, website)
        places = Place.search(domain, order="sequence asc, name asc", limit=limit)
        return [self._serialize_place(pl, website) for pl in places]

    @api.model
    def get_now_playing_movies(self, limit=6, website=None):
        website = website or self.env["website"].get_current_website()
        Movie = self._get_model("guiabh.cinema.movie")
        if not Movie:
            return []
        domain = [
            ("active", "=", True),
            ("website_published", "=", True),
        ]
        if "category" in Movie._fields:
            domain.append(("category", "in", ["now", "premiere"]))
        movies = Movie.search(domain, order="is_featured desc, id desc", limit=limit)
        return [self._serialize_movie(mv) for mv in movies]

    @api.model
    def get_upcoming_matches(self, limit=6, date_window=30, website=None):
        website = website or self.env["website"].get_current_website()
        Match = self._get_model("guiabh.football.match")
        if Match:
            now = fields.Datetime.now()
            end = now + timedelta(days=date_window or 30)
            domain = [
                ("website_published", "=", True),
                ("active", "=", True),
                ("match_datetime", ">=", now),
                ("match_datetime", "<=", end),
            ]
            matches = Match.search(domain, order="match_datetime asc, id asc", limit=limit)
            return [self._serialize_match(mt) for mt in matches]
        return []

    @api.model
    def build_featured_carousel(self, events=None, movies=None, matches=None, places=None, limit=10):
        items = []

        def _extend(source_list):
            for entry in source_list or []:
                if entry.get("image_url"):
                    items.append(entry)

        _extend(events)
        _extend(movies)
        _extend(matches)
        _extend(places)
        if len(items) < limit:
            # allow placeholders without image to avoid empty carousel
            for entry in (events or []) + (movies or []) + (matches or []) + (places or []):
                if entry not in items:
                    items.append(entry)
                    if len(items) >= limit:
                        break
        return items[:limit]

    # Provider API (normalized cards) ------------------------------------
    @api.model
    def provider_events(self, limit=6, website=None):
        """Normalized events from bhz_event_promo or fallback."""
        events = self.get_featured_events(limit=limit, website=website)
        if len(events) < limit:
            events += self.get_upcoming_events(limit=limit - len(events), date_window=45, website=website)
        return [self._normalize_card(ev) for ev in events][:limit]

    @api.model
    def provider_movies(self, limit=6, website=None):
        movies = self.get_now_playing_movies(limit=limit, website=website)
        return [self._normalize_card(mv) for mv in movies][:limit]

    @api.model
    def provider_matches(self, limit=6, website=None):
        matches = self.get_upcoming_matches(limit=limit, date_window=45, website=website)
        return [self._normalize_card(mt) for mt in matches][:limit]

    @api.model
    def provider_places(self, limit=6, website=None):
        places = self.get_featured_places(limit=limit, website=website)
        return [self._normalize_card(pl) for pl in places][:limit]

    @api.model
    def provider_feed(self, limit=20, website=None):
        """Aggregate feed combining events, movies, matches, places."""
        website = website or self.env["website"].get_current_website()
        per_kind = max(1, int(limit / 4))
        feed = []
        feed += self.provider_events(limit=per_kind, website=website)
        feed += self.provider_movies(limit=per_kind, website=website)
        feed += self.provider_matches(limit=per_kind, website=website)
        feed += self.provider_places(limit=per_kind, website=website)
        return feed[:limit]

    @api.model
    def get_banners(self, limit=8, website=None):
        website = website or self.env["website"].get_current_website()
        Banner = self._get_model("guiabh.banner")
        if not Banner:
            # fallback: build banners from featured content
            return self._build_featured_banners(limit=limit, website=website)

        now = fields.Datetime.now()
        domain = [
            ("active", "=", True),
            "|", ("date_start", "=", False), ("date_start", "<=", now),
            "|", ("date_end", "=", False), ("date_end", ">=", now),
        ]
        domain += self._website_domain(Banner, website)
        banners = Banner.search(domain, order="sequence asc, id asc", limit=limit)
        data = []
        for bn in banners:
            img = self._image_url(bn, "image", width=1920, height=800, placeholder=self._placeholder("event"))
            data.append({
                "title": bn.name,
                "subtitle": bn.subtitle or "",
                "image_url": img,
                "link_url": bn.link_url or "#",
            })

        # If no explicit banners, auto-build from featured content without copying records.
        if not data:
            data = self._build_featured_banners(limit=limit, website=website)
        return data

    def _build_featured_banners(self, limit=8, website=None):
        """Build banners from featured content across sources (no duplication)."""
        website = website or self.env["website"].get_current_website()
        items = []

        def _add(entries, kind_label):
            for entry in entries or []:
                items.append({
                    "title": entry.get("title"),
                    "subtitle": ", ".join(entry.get("tags") or []) or kind_label,
                    "image_url": entry.get("image_url") or entry.get("cover") or self._placeholder("event"),
                    "link_url": entry.get("url") or "#",
                    "priority": entry.get("editorial_priority") or 50,
                })

        _add(self.get_featured_events(limit=limit, website=website), "Evento")
        _add(self.get_featured_places(limit=limit, website=website), "Lugar")
        _add(self.get_now_playing_movies(limit=limit, website=website), "Cinema")
        _add(self.get_upcoming_matches(limit=limit, website=website), "Jogo")

        # sort by priority and date-like info if available
        items = sorted(items, key=lambda i: i.get("priority", 50))
        return items[:limit]

    # Fallbacks -----------------------------------------------------------
    def _fallback_events(self, featured=False, limit=6, date_window=30, website=None):
        Event = self._get_model("guiabh.event")
        if not Event:
            return []
        domain = self._published_domain(Event) + self._website_domain(Event, website)
        if featured:
            domain.append(("is_featured", "=", True))
        start_field = "start_datetime" if "start_datetime" in Event._fields else False
        now = fields.Datetime.now()
        if start_field:
            domain.append((start_field, ">=", now))
            if date_window:
                domain.append((start_field, "<=", now + timedelta(days=date_window)))
        order = "is_featured desc, start_datetime asc, id desc" if start_field else "is_featured desc, id desc"
        events = Event.search(domain, order=order, limit=limit)
        return [self._serialize_event(ev, website) for ev in events]

    def _fallback_places(self, limit=6, website=None):
        Place = self._get_model("guiabh.place")
        if not Place:
            return []
        domain = self._published_domain(Place) + self._website_domain(Place, website)
        places = Place.search(domain + [("is_featured", "=", True)], order="is_featured desc, name asc", limit=limit)
        return [self._serialize_place(pl, website) for pl in places]

    # Serializers ---------------------------------------------------------
    def _serialize_event(self, event, website):
        placeholder = self._placeholder("event")
        date_field = "date_begin" if "date_begin" in event._fields else "start_datetime"
        start_dt = getattr(event, date_field, False) if date_field else False
        image_url = (
            self._image_url(event, "promo_cover_image", placeholder=placeholder)
            or self._image_url(event, "cover_image", placeholder=placeholder)
            or self._image_url(event, "image_1920", placeholder=placeholder)
        )
        if not image_url:
            image_url = placeholder
        category = getattr(event, "promo_category_id", False) or getattr(event, "event_type_id", False)
        price_field = getattr(event, "ticket_kind", False)
        price_badge = "Gratuito" if price_field == "free" else False

        url = getattr(event, "website_url", False) or f"/agenda/event/{event.id}"
        badges = ["Evento"]
        if getattr(event, "is_featured", False):
            badges.append("Destaque")
        if price_badge:
            badges.append(price_badge)
        if getattr(event, "price_type", False) == "free":
            badges.append("Gratuito")

        subtitle = (
            getattr(event, "venue_partner_id", False) and event.venue_partner_id.name
        ) or getattr(event, "venue_name", False) or getattr(event, "neighborhood", False) or ""

        meta = []
        if category and hasattr(category, "name"):
            meta.append(category.name)
        region = getattr(event, "region_id", False)
        if region and hasattr(region, "name"):
            meta.append(region.name)

        return {
            "kind": "event",
            "kind_label": "Evento",
            "id": event.id,
            "title": event.name,
            "subtitle": subtitle,
            "description": getattr(event, "promo_short_description", False) or getattr(event, "short_description", False) or "",
            "date_label": self._format_datetime(start_dt),
            "image_url": image_url,
            "url": url,
            "meta": [m for m in meta if m],
            "badges": badges,
            "cta_label": "Ver detalhes",
        }

    def _serialize_place(self, place, website):
        placeholder = self._placeholder("place")
        image_url = (
            self._image_url(place, "image_1920", placeholder=placeholder)
            or self._image_url(place, "cover_image", placeholder=placeholder)
        )
        url = f"/lugares/{place.slug}" if getattr(place, "slug", False) else f"/lugares/{place.id}"
        meta = []
        if getattr(place, "category_id", False) and place.category_id.name:
            meta.append(place.category_id.name)
        if getattr(place, "price_range", False):
            meta.append(place.price_range)
        if getattr(place, "neighborhood", False):
            meta.append(place.neighborhood)
        return {
            "kind": "place",
            "kind_label": "Local",
            "id": place.id,
            "title": place.name,
            "subtitle": getattr(place, "city_id", False) and place.city_id.name or "",
            "description": getattr(place, "short_description", False) or "",
            "image_url": image_url or placeholder,
            "url": url,
            "meta": [m for m in meta if m],
            "badges": ["Local"],
            "cta_label": "Saiba mais",
        }

    def _serialize_movie(self, movie):
        placeholder = self._placeholder("event")
        image_url = self._image_url(movie, "poster_image", placeholder=placeholder) or movie.poster_url or placeholder
        category_label = dict(movie._fields["category"].selection).get(movie.category, movie.category)
        meta = [category_label] if category_label else []
        return {
            "kind": "movie",
            "kind_label": "Cinema",
            "id": movie.id,
            "title": movie.name,
            "subtitle": movie.genre or "",
            "description": movie.release_date or "",
            "image_url": image_url,
            "url": movie.cineart_url or "/cineart",
            "meta": meta,
            "badges": ["Cinema"],
            "cta_label": "Ver detalhes",
        }

    def _serialize_match(self, match):
        placeholder = self._placeholder("event")
        image_url = (
            self._image_url(match.home_team_id, "logo", placeholder="")
            or self._image_url(match.away_team_id, "logo", placeholder="")
            or placeholder
        )
        home_logo = self._image_url(match.home_team_id, "logo", placeholder="")
        away_logo = self._image_url(match.away_team_id, "logo", placeholder="")
        meta = []
        if match.competition:
            meta.append(match.competition)
        if match.city:
            meta.append(match.city)
        badge = ""
        kickoff = match.match_datetime
        if kickoff:
            local_dt = fields.Datetime.context_timestamp(self.env.user, kickoff)
            today = fields.Date.context_today(self.env.user)
            tomorrow = today + timedelta(days=1)
            if local_dt.date() == today:
                badge = "Hoje"
            elif local_dt.date() == tomorrow:
                badge = "Amanhã"
        badges = ["Jogo"]
        if badge:
            badges.append(badge)
        return {
            "kind": "match",
            "kind_label": "Jogo",
            "id": match.id,
            "title": f"{match.home_team_id.name} x {match.away_team_id.name}",
            "subtitle": match.stadium or "",
            "description": match.round_name or "",
            "date_label": self._format_datetime(match.match_datetime),
            "image_url": image_url,
            "url": match.ticket_url or "/futebol/agenda",
            "meta": [m for m in meta if m],
            "badges": badges,
            "cta_label": "Detalhes",
            "home_logo": home_logo,
            "away_logo": away_logo,
        }

    def _normalize_card(self, item):
        """Return a normalized structure shared across providers."""
        return {
            "kind": item.get("kind"),
            "title": item.get("title"),
            "cover": item.get("image_url"),
            "date": item.get("date_label") or "",
            "url": item.get("url"),
            "tags": item.get("meta") or [],
            "is_featured": "Destaque" in (item.get("badges") or []),
        }
