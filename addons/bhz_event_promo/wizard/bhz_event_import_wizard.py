# -*- coding: utf-8 -*-
import base64
import csv
import io
from collections import defaultdict
from datetime import datetime

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class BhzEventImportWizard(models.TransientModel):
    _name = "bhz.event.import.wizard"
    _description = "Importador Guia BH"

    csv_file = fields.Binary(string="Arquivo CSV")
    csv_filename = fields.Char()
    ics_file = fields.Binary(string="Arquivo ICS")
    ics_filename = fields.Char()
    link_url = fields.Char(string="URL (CSV/ICS)")
    link_format = fields.Selection(
        [("csv", "CSV"), ("ics", "ICS")],
        string="Formato do link",
        default="ics",
    )
    default_button_label = fields.Char(
        string="Texto padrão do botão",
        default="Inscrever-se",
    )

    def action_import(self):
        self.ensure_one()
        if not (self.csv_file or self.ics_file or self.link_url):
            raise UserError(_("Envie um CSV, um ICS ou informe uma URL para importar."))

        created_events = self.env["event.event"].sudo().browse()

        if self.csv_file:
            created_events |= self._import_csv_data(base64.b64decode(self.csv_file))
        if self.ics_file:
            created_events |= self._import_ics_data(base64.b64decode(self.ics_file))
        if self.link_url:
            payload = self._download_external_file(self.link_url)
            if self.link_format == "csv":
                created_events |= self._import_csv_data(payload)
            else:
                created_events |= self._import_ics_data(payload)

        if not created_events:
            raise UserError(_("Nenhum evento foi criado. Confira o conteúdo dos arquivos."))

        self.env.user.notify_success(
            message=_("Foram importados %s eventos.", len(created_events))
        )
        return {"type": "ir.actions.act_window_close"}

    # CSV ---------------------------------------------------------------------
    def _import_csv_data(self, data_bytes):
        stream = io.StringIO(data_bytes.decode("utf-8-sig"))
        reader = csv.DictReader(stream)
        Event = self.env["event.event"].sudo()
        created = Event.browse()
        for idx, row in enumerate(reader, start=1):
            vals = self._prepare_vals_from_csv(row)
            if not vals:
                continue
            try:
                new_event = Event.create(vals)
            except Exception as err:
                raise UserError(_("Erro ao criar evento na linha %(line)s: %(msg)s", line=idx, msg=err))
            created |= new_event
        return created

    def _prepare_vals_from_csv(self, row):
        name = (row.get("name") or "").strip()
        date_begin = self._parse_datetime(row.get("date_begin"))
        if not name or not date_begin:
            return False

        date_end = self._parse_datetime(row.get("date_end")) or date_begin
        external_url = (row.get("external_url") or "").strip()
        button_label = (row.get("button_label") or self.default_button_label).strip()
        category = self._find_category(row.get("category"))
        venue = self._get_or_create_venue(row.get("venue"))

        vals = self._base_event_vals()
        vals.update(
            {
                "name": name,
                "date_begin": date_begin,
                "date_end": date_end,
                "registration_external_url": external_url or False,
                "registration_button_label": button_label or self.default_button_label,
                "promo_category_id": category.id if category else False,
                "neighborhood": (row.get("neighborhood") or "").strip() or False,
                "venue_partner_id": venue.id if venue else False,
                "ticket_kind": self._map_ticket_kind(row.get("ticket_kind")),
                "age_rating": self._map_age_rating(row.get("age_rating")),
                "producer_name": (row.get("producer_name") or "").strip() or False,
                "is_accessible_pcd": self._to_bool(row.get("is_accessible_pcd")),
            }
        )
        return vals

    # ICS --------------------------------------------------------------------
    def _import_ics_data(self, data_bytes):
        text = data_bytes.decode("utf-8", errors="ignore")
        lines = self._unfold_ics_lines(text.splitlines())
        blocks = self._extract_ics_blocks(lines)
        Event = self.env["event.event"].sudo()
        created = Event.browse()
        for block in blocks:
            vals = self._prepare_vals_from_ics(block)
            if not vals:
                continue
            new_event = Event.create(vals)
            created |= new_event
        return created

    def _extract_ics_blocks(self, lines):
        blocks = []
        current = defaultdict(str)
        inside = False
        for line in lines:
            if line == "BEGIN:VEVENT":
                inside = True
                current = defaultdict(str)
                continue
            if line == "END:VEVENT":
                inside = False
                blocks.append(dict(current))
                current = defaultdict(str)
                continue
            if not inside or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.split(";", 1)[0].upper()
            current[key] = value.strip()
        return blocks

    def _prepare_vals_from_ics(self, data):
        name = data.get("SUMMARY")
        start_raw = data.get("DTSTART")
        if not name or not start_raw:
            return False
        date_begin = self._parse_ics_datetime(start_raw)
        if not date_begin:
            return False
        date_end = self._parse_ics_datetime(data.get("DTEND")) or date_begin

        location = (data.get("LOCATION") or "").strip()
        venue = False
        neighborhood = False
        if location:
            if "-" in location:
                venue_name, neighborhood = [part.strip() for part in location.split("-", 1)]
                venue = self._get_or_create_venue(venue_name)
            else:
                venue = self._get_or_create_venue(location)
        description = (data.get("DESCRIPTION") or "").strip()
        short_desc = description[:180] if description else False
        category = self._find_category(data.get("CATEGORIES"))

        vals = self._base_event_vals()
        vals.update(
            {
                "name": name.strip(),
                "date_begin": date_begin,
                "date_end": date_end,
                "registration_external_url": (data.get("URL") or "").strip() or False,
                "registration_button_label": self.default_button_label,
                "promo_short_description": short_desc,
                "promo_category_id": category.id if category else False,
                "venue_partner_id": venue.id if venue else False,
                "neighborhood": neighborhood or False,
            }
        )
        return vals

    # Helpers -----------------------------------------------------------------
    def _base_event_vals(self):
        return {
            "registration_mode": "external",
            "show_on_public_agenda": True,
        }

    def _parse_datetime(self, value):
        if not value:
            return None
        try:
            return fields.Datetime.from_string(value)
        except Exception:
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return None

    def _parse_ics_datetime(self, value):
        if not value:
            return None
        value = value.strip()
        if "T" in value:
            clean = value.rstrip("Z")
            fmt = "%Y%m%dT%H%M%S" if len(clean) == 15 else "%Y%m%dT%H%M"
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                return None
        try:
            return datetime.strptime(value, "%Y%m%d")
        except ValueError:
            return None

    def _find_category(self, name):
        if not name:
            return False
        clean = name.strip()
        EventType = self.env["event.type"].sudo()
        category = EventType.search([("name", "=", clean)], limit=1)
        if not category:
            category = EventType.search([("name", "ilike", clean)], limit=1)
        return category

    def _get_or_create_venue(self, name):
        if not name:
            return False
        clean = name.strip()
        if not clean:
            return False
        Partner = self.env["res.partner"].sudo()
        venue = Partner.search([("name", "=", clean)], limit=1)
        if not venue:
            venue = Partner.create({"name": clean, "company_type": "company"})
        return venue

    def _map_ticket_kind(self, value):
        if not value:
            return "unknown"
        clean = value.strip().lower()
        mapping = {
            "free": "free",
            "gratuito": "free",
            "pago": "paid",
            "paid": "paid",
        }
        return mapping.get(clean, "unknown")

    def _map_age_rating(self, value):
        if not value:
            return "l"
        clean = value.strip().lower()
        mapping = {
            "l": "l",
            "livre": "l",
            "10": "10",
            "12": "12",
            "14": "14",
            "16": "16",
            "18": "18",
        }
        clean = clean.replace("+", "")
        return mapping.get(clean, "l")

    def _to_bool(self, value):
        return str(value).strip().lower() in ("1", "true", "yes", "y", "sim")

    def _unfold_ics_lines(self, lines):
        unfolded = []
        for raw in lines:
            line = raw.rstrip("\r\n")
            if line.startswith((" ", "\t")) and unfolded:
                unfolded[-1] += line.lstrip()
            else:
                unfolded.append(line)
        return unfolded

    def _download_external_file(self, url):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as err:
            raise UserError(_("Erro ao baixar o arquivo: %s") % err)
        return response.content
