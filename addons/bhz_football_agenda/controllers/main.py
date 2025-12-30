from collections import OrderedDict
from datetime import datetime, time, timedelta
from urllib.parse import urlencode

from odoo import fields, http
from odoo.http import request

try:
    from odoo.tools.misc import format_datetime as misc_format_datetime
except Exception:
    misc_format_datetime = None

class BhzFootballAgendaController(http.Controller):

    @http.route([
        "/futebol/agenda",
        "/futebol/agenda/<string:team_slug>",
    ], type="http", auth="public", website=True, sitemap=True)
    def football_agenda(self, team_slug=None, **kwargs):
        Team = request.env["bhz.football.team"].sudo()
        Match = request.env["bhz.football.match"].sudo()

        teams = Team.search([("website_published", "=", True), ("active", "=", True)], order="name asc")

        selected_team = None
        domain = [
            ("website_published", "=", True),
            ("active", "=", True),
        ]

        if team_slug:
            selected_team = Team.search([("slug", "=", team_slug), ("website_published", "=", True), ("active", "=", True)], limit=1)
            if selected_team:
                domain.append(("team_ids", "in", selected_team.id))

        filters = {
            "date_from": request.params.get("date_from") or "",
            "date_to": request.params.get("date_to") or "",
            "team_id": request.params.get("team_id") or "",
            "competition": request.params.get("competition") or "",
        }

        def _parse_date(value, end=False):
            if not value:
                return False
            try:
                parsed = fields.Date.from_string(value)
                if not parsed:
                    return False
                if end:
                    return datetime.combine(parsed, time.max)
                return datetime.combine(parsed, time.min)
            except Exception:
                return False

        date_from_dt = _parse_date(filters["date_from"])
        date_to_dt = _parse_date(filters["date_to"], end=True)
        if date_from_dt:
            domain.append(("match_datetime", ">=", fields.Datetime.to_string(date_from_dt)))
        if date_to_dt:
            domain.append(("match_datetime", "<=", fields.Datetime.to_string(date_to_dt)))

        if filters["team_id"]:
            try:
                team_id_int = int(filters["team_id"])
                domain.append(("team_ids", "in", team_id_int))
            except ValueError:
                filters["team_id"] = ""

        if filters["competition"]:
            domain.append(("competition", "=", filters["competition"]))

        has_filters = any(
            [
                date_from_dt,
                date_to_dt,
                filters["team_id"],
                filters["competition"],
                bool(team_slug),
            ]
        )
        if not has_filters:
            domain.append(("match_datetime", ">=", fields.Datetime.to_string(fields.Datetime.now())))

        matches = Match.search(domain, order="match_datetime asc", limit=100)

        def _fmt(dt):
            if not dt:
                return ""
            if misc_format_datetime:
                try:
                    return misc_format_datetime(request.env, dt)
                except TypeError:
                    pass
                except Exception:
                    pass
            return fields.Datetime.to_string(dt)

        tz_name = request.context.get("tz") or request.env.user.tz or "UTC"

        def _to_local(dt):
            if not dt:
                return None
            user = request.env.user
            return fields.Datetime.context_timestamp(user.with_context(tz=tz_name), dt)

        today_local = fields.Date.context_today(request.env.user.with_context(tz=tz_name))
        tomorrow_local = today_local + timedelta(days=1)

        def _badge_label(local_dt):
            if not local_dt:
                return ""
            local_date = local_dt.date()
            if local_date == today_local:
                return "Hoje"
            if local_date == tomorrow_local:
                return "Amanhã"
            return ""

        def _gcal_url(match):
            start_dt = fields.Datetime.from_string(match.match_datetime) if match.match_datetime else None
            if not start_dt:
                return False
            end_dt = start_dt + timedelta(hours=2)
            start_str = start_dt.strftime("%Y%m%dT%H%M%SZ")
            end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")
            title = f"{match.home_team_id.name} x {match.away_team_id.name}"
            if match.competition:
                title += f" - {match.competition}"
            location_parts = [part for part in [match.stadium, match.city] if part]
            location = " - ".join(location_parts)
            details_parts = []
            if match.stadium or match.city:
                details_parts.append(location or "")
            if match.broadcast:
                details_parts.append(f"Transmissão: {match.broadcast}")
            if match.ticket_url:
                details_parts.append(f"Ingressos: {match.ticket_url}")
            if match.round_name:
                details_parts.append(f"Rodada: {match.round_name}")
            details = "\n".join(filter(None, details_parts))
            params = {
                "action": "TEMPLATE",
                "text": title,
                "dates": f"{start_str}/{end_str}",
                "details": details,
                "location": location,
            }
            return "https://calendar.google.com/calendar/render?%s" % urlencode(params)

        def _logo_url(team):
            if not team or not team.id or not team.logo:
                return False
            return "/web/image/%s/%s/logo" % (team._name, team.id)

        month_names = [
            "Janeiro",
            "Fevereiro",
            "Março",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ]

        groups_map = OrderedDict()
        for match in matches:
            match_dt = match.match_datetime
            if match_dt:
                key = match_dt.strftime("%Y-%m")
                label = "{month} {year}".format(month=month_names[match_dt.month - 1], year=match_dt.year)
            else:
                key = "sem-data"
                label = "Sem data"
            groups_map.setdefault(key, {"label": label, "items": []})
            local_dt = _to_local(match_dt)
            badge = _badge_label(local_dt)
            groups_map[key]["items"].append(
                {
                    "id": match.id,
                    "home_team_name": match.home_team_id.name,
                    "home_team_logo": _logo_url(match.home_team_id),
                    "away_team_name": match.away_team_id.name,
                    "away_team_logo": _logo_url(match.away_team_id),
                    "competition": match.competition,
                    "stadium": match.stadium,
                    "city": match.city,
                    "round_name": match.round_name,
                    "broadcast": match.broadcast,
                    "ticket_url": match.ticket_url,
                    "match_datetime_str": _fmt(match.match_datetime),
                    "badge_label": badge,
                    "gcal_url": _gcal_url(match),
                }
            )

        groups = list(groups_map.values())

        base_comp_domain = [
            ("website_published", "=", True),
            ("active", "=", True),
        ]
        competition_groups = Match.read_group(base_comp_domain, ["competition"], ["competition"])
        competitions = sorted(filter(None, (grp["competition"] for grp in competition_groups)))

        return request.render(
            "bhz_football_agenda.page_football_agenda",
            {
                "teams": teams,
                "selected_team": selected_team,
                "groups": groups,
                "competitions": competitions,
                "filters": filters,
            },
        )
