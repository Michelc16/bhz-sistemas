# -*- coding: utf-8 -*-
import calendar
import json
import logging
from collections import defaultdict, OrderedDict
from datetime import date, datetime, time, timedelta

from babel.dates import format_date
from urllib.parse import urlencode as py_urlencode

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GuiaBHAgendaController(http.Controller):

    LIST_VIEW = "list"
    MONTH_VIEW = "month"
    WEEK_VIEW = "week"
    VALID_VIEWS = {LIST_VIEW, MONTH_VIEW, WEEK_VIEW}

    @http.route(["/agenda"], type="http", auth="public", website=True, sitemap=True)
    def guiabh_agenda(self, **kw):
        return self._render_agenda_page(category_record=None, **kw)

    @http.route("/event", type="http", auth="public", website=True, sitemap=False)
    def redirect_event_root(self, **kwargs):
        """Keep legacy /event URL working by redirecting to the new agenda."""
        return request.redirect("/agenda", code=301)

    @http.route(
        ["/agenda/c/<model('event.type'):category_record>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def guiabh_agenda_category(self, category_record, **kw):
        return self._render_agenda_page(category_record=category_record, **kw)

    # Helpers -----------------------------------------------------------------
    def _render_agenda_page(self, category_record=None, **kw):
        filters = self._extract_filters(category_record=category_record)
        base_domain = self._base_agenda_domain()
        domain = self._build_domain(filters, base_domain=base_domain)
        events_model = request.env["event.event"].sudo()
        events = events_model.search(domain, order="date_begin asc")
        snapshot = [(ev.id, ev.name) for ev in events[:5]]
        _logger.info("Agenda domain used: %s -> %s eventos | sample=%s", domain, len(events), snapshot)
        if not events:
            fallback = events_model.search([], order="write_date desc, id desc", limit=5)
            _logger.info(
                "Agenda fallback snapshot=%s",
                self._serialize_for_log(fallback),
            )

        venues = self._get_available_venues(base_domain)
        categories = request.env["event.type"].sudo().search([], order="name asc")
        base_path = request.httprequest.path
        base_params, multi_params = self._build_base_query(filters)
        view_urls = self._build_view_urls(base_path, base_params, multi_params, filters)

        context = {
            "events": events,
            "categories": categories,
            "active_category": filters["category_id"],
            "search": filters["search"],
            "view_mode": filters["view"],
            "price_filter": filters["price"],
            "featured_filter": filters["featured"],
            "neighborhood_filter": filters["neighborhood"],
            "venue_filter": filters["venue_id"],
            "available_venues": venues,
            "filter_action": base_path,
            "view_urls": view_urls,
            "base_query": base_params,
            "multi_query": multi_params,
            "category_groups": [],
        }

        if filters["view"] == self.MONTH_VIEW:
            month_info = self._build_month_info(events, filters, base_path, base_params, multi_params)
            context.update({"month_info": month_info})
        elif filters["view"] == self.WEEK_VIEW:
            week_info = self._build_week_info(events, filters, base_path, base_params, multi_params)
            context.update({"week_info": week_info})
        elif filters["view"] == self.LIST_VIEW:
            context["category_groups"] = self._group_events_by_category(events)

        return request.render("bhz_event_promo.bhz_agenda_page", context)

    @http.route(
        ["/agenda/event/<model('event.event'):event>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def guiabh_event_detail(self, event, **kwargs):
        return self._render_event_detail(event)

    @http.route(
        [
            "/event/<model('event.event'):event>",
            "/event/<model('event.event'):event>/register",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def odoo_event_detail_override(self, event, **kwargs):
        """Override standard website_event page to use Guia BH layout."""
        return self._render_event_detail(event)

    def _extract_filters(self, category_record=None):
        args = request.httprequest.args
        today = fields.Date.context_today(request.env.user)
        view = args.get("view") or self.LIST_VIEW
        if view not in self.VALID_VIEWS:
            view = self.LIST_VIEW

        category_id = category_record.id if category_record else self._parse_int(args.get("category"))
        search = (args.get("search") or "").strip()
        price = (args.get("price") or "all").lower()
        if price not in ("free", "paid", "all"):
            price = "all"

        featured = (args.get("featured") or "").lower() in ("1", "true", "yes", "y", "sim")
        neighborhood = (args.get("neighborhood") or "").strip()
        venue_id = self._parse_int(args.get("venue"))
        filters = {
            "view": view,
            "category_id": category_id,
            "search": search,
            "price": price,
            "featured": featured,
            "neighborhood": neighborhood,
            "venue_id": venue_id,
        }

        if view == self.MONTH_VIEW:
            year = self._parse_int(args.get("y")) or today.year
            month = self._parse_int(args.get("m")) or today.month
            month = min(max(month, 1), 12)
            filters["month_year"] = (year, month)
        elif view == self.WEEK_VIEW:
            week_date = self._parse_date(args.get("date")) or today
            filters["week_date"] = week_date

        return filters

    def _base_agenda_domain(self):
        Event = request.env["event.event"]
        domain = [("show_on_public_agenda", "=", True)]

        Stage = request.env["event.stage"].sudo() if "stage_id" in Event._fields else False
        stage_domain = False
        if Stage:
            announced_stage = Stage.search(
                [("name", "in", ["Anunciado", "Announced"])],
                order="sequence asc",
                limit=1,
            )
            if announced_stage and announced_stage.sequence:
                stage_domain = ("stage_id.sequence", ">=", announced_stage.sequence)
            elif announced_stage:
                stage_domain = ("stage_id", "in", announced_stage.ids)
        if stage_domain:
            domain.append(stage_domain)

        if "state" in Event._fields:
            state_field = Event._fields["state"]
            selection_values = {value for value, _label in (state_field.selection or [])}
            if "cancel" in selection_values:
                domain.append(("state", "!=", "cancel"))

        if "date_end" in Event._fields:
            now = fields.Datetime.now()
            domain += [
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", now),
            ]
        elif "date_begin" in Event._fields:
            domain.append(("date_begin", ">=", fields.Datetime.now()))

        if "website_id" in Event._fields:
            current_website = request.website
            if current_website:
                domain += ["|", ("website_id", "=", False), ("website_id", "=", current_website.id)]
        return domain

    def _render_event_detail(self, event):
        event = event.sudo()
        return request.render(
            "bhz_event_promo.bhz_event_detail",
            {
                "event": event,
            },
        )

    @http.route(
        "/bhz_event_promo/snippet/announced_events",
        type="json",
        auth="public",
        website=True,
    )
    def snippet_announced_events_data(self, category_ids=None, limit=12, order_mode="recent"):
        limit = self._sanitize_limit(limit)
        order_mode = self._sanitize_order_mode(order_mode)
        parsed_category_ids = self._parse_category_ids(category_ids)
        events = (
            request.env["event.event"]
            .sudo()
            .guiabh_get_announced_events(limit=limit, category_ids=parsed_category_ids, order_mode=order_mode)
        )
        html = request.env["ir.ui.view"]._render_template(
            "bhz_event_promo.guiabh_announced_events_cards",
            {"events": events},
        )
        return {"html": html, "has_events": bool(events)}

    def _sanitize_limit(self, limit):
        try:
            limit_value = int(limit)
        except (ValueError, TypeError):
            limit_value = 12
        return max(1, min(limit_value, 24))

    def _sanitize_order_mode(self, order_mode):
        if isinstance(order_mode, str):
            lowered = order_mode.lower()
            if lowered in ("recent", "popular"):
                return lowered
        return "recent"

    def _parse_category_ids(self, category_ids):
        raw_ids = category_ids or []
        if isinstance(raw_ids, str):
            try:
                raw_ids = json.loads(raw_ids)
            except ValueError:
                raw_ids = []
        parsed = []
        for entry in raw_ids:
            if isinstance(entry, dict):
                entry = entry.get("id")
            try:
                entry_id = int(entry)
            except (ValueError, TypeError):
                continue
            if entry_id:
                parsed.append(entry_id)
        return parsed

    def _build_domain(self, filters, base_domain=None):
        domain = list(base_domain or self._base_agenda_domain())
        if filters["category_id"]:
            domain.append(("promo_category_id", "=", filters["category_id"]))
        if filters["search"]:
            domain += ["|", ("name", "ilike", filters["search"]), ("promo_short_description", "ilike", filters["search"])]
        if filters["price"] == "free":
            domain.append(("ticket_kind", "=", "free"))
        elif filters["price"] == "paid":
            domain.append(("ticket_kind", "=", "paid"))
        if filters["featured"]:
            domain.append(("is_featured", "=", True))
        if filters["neighborhood"]:
            domain.append(("neighborhood", "ilike", filters["neighborhood"]))
        if filters["venue_id"]:
            domain.append(("venue_partner_id", "=", filters["venue_id"]))
        return domain

    def _build_month_info(self, events, filters, base_path, base_params, multi_params):
        year, month = filters.get("month_year", (None, None))
        today = fields.Date.context_today(request.env.user)
        if not year or not month:
            year, month = today.year, today.month

        month_start = date(year, month, 1)
        next_year, next_month = self._shift_month(year, month, 1)
        prev_year, prev_month = self._shift_month(year, month, -1)
        period_start_dt = datetime.combine(month_start, time.min)
        period_end_dt = datetime.combine(date(next_year, next_month, 1), time.min)

        month_events = self._filter_events_by_range(events, period_start_dt, period_end_dt)
        mapping = self._map_events_by_day(month_events, month_start, date(next_year, next_month, 1))

        cal = calendar.Calendar()
        weeks = []
        today_date = today
        for week in cal.monthdatescalendar(year, month):
            row = []
            for day in week:
                row.append(
                    {
                        "date": day,
                        "in_month": day.month == month,
                        "is_today": day == today_date,
                        "events": mapping.get(day, []),
                    }
                )
            weeks.append(row)

        lang = request.env.lang or "en_US"
        month_label = format_date(month_start, format="LLLL yyyy", locale=lang)

        prev_params = dict(base_params, view=self.MONTH_VIEW, y=prev_year, m=prev_month)
        next_params = dict(base_params, view=self.MONTH_VIEW, y=next_year, m=next_month)
        current_params = dict(base_params, view=self.MONTH_VIEW, y=year, m=month)

        return {
            "weeks": weeks,
            "label": month_label,
            "prev_url": self._build_url(base_path, prev_params, multi_params),
            "next_url": self._build_url(base_path, next_params, multi_params),
            "current_url": self._build_url(base_path, current_params, multi_params),
            "year": year,
            "month": month,
        }

    def _build_week_info(self, events, filters, base_path, base_params, multi_params):
        target_date = filters.get("week_date") or fields.Date.context_today(request.env.user)
        if isinstance(target_date, str):
            target_date = self._parse_date(target_date) or fields.Date.context_today(request.env.user)
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=7)

        period_start_dt = datetime.combine(week_start, time.min)
        period_end_dt = datetime.combine(week_end, time.min)

        week_events = self._filter_events_by_range(events, period_start_dt, period_end_dt)
        mapping = self._map_events_by_day(week_events, week_start, week_end)

        days = []
        lang = request.env.lang or "en_US"
        today = fields.Date.context_today(request.env.user)
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            days.append(
                {
                    "date": day,
                    "label": format_date(day, format="EEE dd/MM", locale=lang),
                    "events": mapping.get(day, []),
                    "is_today": day == today,
                }
            )

        prev_date = week_start - timedelta(days=7)
        next_date = week_start + timedelta(days=7)
        week_label = "{} – {}".format(
            format_date(week_start, format="dd MMM", locale=lang),
            format_date(week_end - timedelta(days=1), format="dd MMM yyyy", locale=lang),
        )

        prev_params = dict(base_params, view=self.WEEK_VIEW, date=prev_date.isoformat())
        next_params = dict(base_params, view=self.WEEK_VIEW, date=next_date.isoformat())
        current_params = dict(base_params, view=self.WEEK_VIEW, date=week_start.isoformat())

        return {
            "days": days,
            "label": week_label,
            "prev_url": self._build_url(base_path, prev_params, multi_params),
            "next_url": self._build_url(base_path, next_params, multi_params),
            "current_date": week_start,
            "current_url": self._build_url(base_path, current_params, multi_params),
        }

    def _filter_events_by_range(self, events, start_dt, end_dt):
        def _event_end(ev):
            return ev.date_end or ev.date_begin or end_dt

        return events.filtered(
            lambda ev: ev.date_begin
            and ev.date_begin < end_dt
            and _event_end(ev) >= start_dt
        )

    def _map_events_by_day(self, events, date_start, date_end):
        mapping = defaultdict(list)
        for event in events:
            start_dt = event.date_begin or fields.Datetime.now()
            end_dt = event.date_end or start_dt
            start_day = start_dt.date()
            end_day = end_dt.date()
            day_cursor = max(start_day, date_start)
            last_day = min(end_day, date_end - timedelta(days=1))
            while day_cursor <= last_day:
                mapping[day_cursor].append(event)
                day_cursor += timedelta(days=1)
        return mapping

    def _group_events_by_category(self, events):
        groups = OrderedDict()
        for event in events:
            category = event.promo_category_id or getattr(event, "event_type_id", False)
            category_id = category.id if category else False
            key = category_id or 0
            if key not in groups:
                groups[key] = {
                    "category_id": category_id,
                    "category": category,
                    "category_name": category.name if category else "Outros eventos",
                    "events": [],
                }
            groups[key]["events"].append(event)

        def sort_key(group):
            category = group["category"]
            if category:
                sequence = getattr(category, "sequence", 0) or 0
                name = (category.name or "").lower()
            else:
                sequence = 9999
                name = "zzz"
            return (sequence, name)

        return sorted(groups.values(), key=sort_key)

    def _build_base_query(self, filters):
        params = {}
        if filters["category_id"]:
            params["category"] = str(filters["category_id"])
        if filters["search"]:
            params["search"] = filters["search"]
        if filters["price"] in ("free", "paid"):
            params["price"] = filters["price"]
        if filters["featured"]:
            params["featured"] = "1"
        if filters["neighborhood"]:
            params["neighborhood"] = filters["neighborhood"]
        if filters["venue_id"]:
            params["venue"] = str(filters["venue_id"])
        multi = {}
        return params, multi

    def _serialize_for_log(self, events):
        return [
            {
                "id": ev.id,
                "name": ev.name,
                "show_on_public_agenda": ev.show_on_public_agenda,
                "is_published": getattr(ev, "is_published", None),
                "website_published": getattr(ev, "website_published", None),
                "website_id": ev.website_id.id if ev.website_id else False,
                "state": getattr(ev, "state", None),
                "date_begin": ev.date_begin,
            }
            for ev in events
        ]

    def _build_view_urls(self, base_path, base_params, multi_params, filters):
        urls = {}
        urls[self.LIST_VIEW] = self._build_url(base_path, dict(base_params), multi_params)
        if filters.get("month_year"):
            year, month = filters["month_year"]
        else:
            today = fields.Date.context_today(request.env.user)
            year, month = today.year, today.month
        month_params = dict(base_params, view=self.MONTH_VIEW, y=year, m=month)
        urls[self.MONTH_VIEW] = self._build_url(base_path, month_params, multi_params)

        week_date = filters.get("week_date") or fields.Date.context_today(request.env.user)
        if isinstance(week_date, str):
            week_date = self._parse_date(week_date) or fields.Date.context_today(request.env.user)
        week_params = dict(base_params, view=self.WEEK_VIEW, date=week_date.isoformat())
        urls[self.WEEK_VIEW] = self._build_url(base_path, week_params, multi_params)
        return urls

    def _build_url(self, base_path, params, multi_params):
        query_pairs = []
        for key, value in params.items():
            if value in (None, False, "", []):
                continue
            query_pairs.append((key, value))
        for key, values in multi_params.items():
            for value in values:
                query_pairs.append((key, value))
        query = py_urlencode(query_pairs, doseq=True)
        return "{}?{}".format(base_path, query) if query else base_path

    def _shift_month(self, year, month, delta):
        month += delta
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        return year, month

    def _parse_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return fields.Date.from_string(value)
        except Exception:
            return None

    def _get_available_venues(self, domain):
        Event = request.env["event.event"].sudo()
        grouped = Event.read_group(domain, ["venue_partner_id"], ["venue_partner_id"])
        venue_ids = [res["venue_partner_id"][0] for res in grouped if res.get("venue_partner_id")]
        return request.env["res.partner"].sudo().browse(venue_ids).sorted(lambda p: p.name or "")
