# -*- coding: utf-8 -*-
import logging
import base64
import json
from datetime import datetime
from urllib.parse import urlparse

import pytz
import requests
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class EventEvent(models.Model):
    _inherit = "event.event"

    is_third_party = fields.Boolean(string="Evento de terceiro", default=False)
    third_party_name = fields.Char(string="Organizador / Fonte (texto livre)")
    third_party_partner_id = fields.Many2one("res.partner", string="Organizador (contato)")
    promo_description_html = fields.Html(
        string="Descrição (Guia BH)",
        sanitize=True,
        translate=False,
        help="Descrição rica exibida na página pública do evento.",
    )

    # Modo do botão: interno (Odoo), externo (link) ou somente divulgação
    registration_mode = fields.Selection(
        [
            ("internal", "Inscrição/Venda pelo meu site (Odoo)"),
            ("external", "Redirecionar para link externo"),
            ("disclosure_only", "Somente divulgação (sem link / sem ingressos)"),
        ],
        string="Modo do botão de inscrição",
        default="internal",
        required=True,
    )

    registration_button_label = fields.Char(
        string="Texto do botão",
        default="Inscrever-se",
        help="Ex.: Comprar ingresso, Ver no Sympla, Garantir vaga…",
    )

    registration_external_url = fields.Char(
        string="Link externo de inscrição/venda",
        help="Cole aqui o link do Sympla/Central dos Eventos/etc. Usado quando o modo for externo.",
    )

    promo_cover_image = fields.Image(
        string="Imagem de divulgação (capa/banner)",
        max_width=1920,
        max_height=1080,
        help="Imagem principal para aparecer na agenda e na página do evento.",
    )

    promo_short_description = fields.Char(
        string="Chamada curta (lista/agenda)",
        help="Linha curta para a lista (ex.: 'Return to South America 2026')",
    )
    age_rating = fields.Selection(
        [
            ("l", "Livre"),
            ("10", "10 anos"),
            ("12", "12 anos"),
            ("14", "14 anos"),
            ("16", "16 anos"),
            ("18", "18 anos"),
        ],
        string="Classificação indicativa",
        default="l",
    )
    is_accessible_pcd = fields.Boolean(string="Acessível para PCD", default=False)
    producer_name = fields.Char(string="Produtor / Realização")
    is_featured = fields.Boolean(string="Destaque na agenda", default=False)
    is_sponsored = fields.Boolean(string="Patrocinado", default=False)
    ticket_kind = fields.Selection(
        [
            ("unknown", "Não informado"),
            ("free", "Gratuito"),
            ("paid", "Pago"),
        ],
        string="Tipo de ingresso",
        default="unknown",
    )
    venue_partner_id = fields.Many2one(
        "res.partner",
        string="Local / Casa do evento",
    )
    neighborhood = fields.Char(string="Bairro")

    promo_category_id = fields.Many2one(
        "event.type",
        string="Categoria (Tipo de evento)",
        help="Use como categoria para filtrar na Agenda do site.",
    )

    show_on_public_agenda = fields.Boolean(
        string="Mostrar na Agenda pública",
        default=True,
        help="Se marcado, aparece na página /agenda.",
    )
    bhz_website_visit_count = fields.Integer(
        string="Visualizações no site (GuiaBH)",
        default=0,
        help="Usado para ordenar os eventos mais acessados nos blocos do site.",
    )
    external_source = fields.Char(string="Fonte externa", index=True)
    external_id = fields.Char(string="ID externo", index=True)
    external_url = fields.Char(string="URL do evento externo")
    external_last_sync = fields.Datetime(string="Última sincronização externa")

    _sql_constraints = [
        ("bhz_event_external_unique", "unique(external_source, external_id)", "A combinação de Fonte externa e ID externo deve ser única."),
    ]
    auto_remove_after_event = fields.Selection(
        [
            ("none", "Não fazer nada"),
            ("unpublish", "Despublicar após o evento"),
            ("delete", "Excluir após o evento"),
        ],
        string="Ação pós-evento",
        default="unpublish",
        help="Define o que acontece automaticamente quando o evento já passou.",
    )

    @api.constrains("registration_mode", "registration_external_url")
    def _check_external_url(self):
        for ev in self:
            if ev.registration_mode == "external" and not ev.registration_external_url:
                # não bloqueia salvar se você preferir; mas o ideal é forçar.
                # Para forçar, descomente a linha abaixo:
                # raise ValidationError("Informe o Link externo quando o modo for 'Redirecionar'.")
                pass

    def init(self):
        super().init()
        self._migrate_promo_description_html()
        self._migrate_registration_mode_values()

    def _existing_columns(self):
        self.env.cr.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_name = 'event_event'
               AND table_schema = current_schema()
            """
        )
        return {row[0] for row in self.env.cr.fetchall()}

    def _migrate_promo_description_html(self):
        columns = self._existing_columns()
        target_col = "promo_description_html"
        if target_col not in columns:
            return

        for source in (
            "public_description_html",
            "promo_html_description",
            "third_party_description_html",
            "third_party_description",
            "organizer_description",
        ):
            if source not in columns:
                continue
            self.env.cr.execute(
                f"""
                UPDATE event_event
                   SET {target_col} = {source}
                 WHERE ({target_col} IS NULL OR {target_col} = '')
                   AND {source} IS NOT NULL
                   AND {source} != ''
                """
            )

    def _migrate_registration_mode_values(self):
        columns = self._existing_columns()
        if "registration_mode" not in columns:
            return
        self.env.cr.execute(
            """
            UPDATE event_event
               SET registration_mode = 'disclosure_only'
             WHERE registration_mode IN ('promo', 'none')
            """
        )

    def _prepare_public_events_domain(
        self,
        require_announced=True,
        require_featured=False,
        require_image=False,
        category_ids=None,
    ):
        domain = [("show_on_public_agenda", "=", True)]

        if require_featured and "is_featured" in self._fields:
            domain.append(("is_featured", "=", True))

        if require_image and ("promo_cover_image" in self._fields or "image_1920" in self._fields):
            # Accept either custom promo cover or the standard event image as fallback.
            domain += ["|", ("promo_cover_image", "!=", False), ("image_1920", "!=", False)]

        if category_ids and "promo_category_id" in self._fields:
            category_ids = [int(cid) for cid in category_ids if cid]
            if category_ids:
                domain.append(("promo_category_id", "in", category_ids))

        website = getattr(request, "website", False)
        if website and "website_id" in self._fields:
            domain += ["|", ("website_id", "=", False), ("website_id", "=", website.id)]

        if require_announced and "stage_id" in self._fields:
            Stage = self.env["event.stage"].sudo()
            announced_stage = Stage.search(
                [("name", "in", ["Anunciado", "Announced"])],
                order="sequence asc",
                limit=1,
            )
            if announced_stage and announced_stage.sequence:
                domain.append(("stage_id.sequence", ">=", announced_stage.sequence))
            elif announced_stage:
                domain.append(("stage_id", "in", announced_stage.ids))

        if "state" in self._fields:
            state_field = self._fields["state"]
            selection_values = {value for value, _label in (state_field.selection or [])}
            if "published" in selection_values:
                domain.append(("state", "=", "published"))
            elif "cancel" in selection_values:
                domain.append(("state", "!=", "cancel"))

        now = fields.Datetime.now()
        if "date_end" in self._fields:
            domain += [
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", now),
            ]
        elif "date_begin" in self._fields:
            domain.append(("date_begin", ">=", now))

        if "website_published" in self._fields:
            domain.append(("website_published", "=", True))
        elif "is_published" in self._fields:
            domain.append(("is_published", "=", True))

        return domain

    @api.model
    def guiabh_get_featured_events(self, limit=12):
        """Return featured events for website widgets; always require a promo image."""
        domain = self._prepare_public_events_domain(require_featured=True, require_image=True)
        events = self.sudo().search(domain, limit=limit, order="write_date desc, date_begin asc, id desc")
        if not events:
            domain = self._prepare_public_events_domain(require_featured=False, require_image=True)
            events = self.sudo().search(domain, limit=limit, order="write_date desc, date_begin asc, id desc")
        return events

    @api.model
    def guiabh_get_announced_events(self, limit=12, category_ids=None, order_mode="recent"):
        """Return announced events with promotional images for snippets."""
        domain = self._prepare_public_events_domain(
            require_image=True,
            category_ids=category_ids,
        )
        order = self._get_announced_events_order(order_mode)
        return self.sudo().search(domain, limit=limit, order=order)

    def _get_announced_events_order(self, order_mode):
        allowed = (order_mode or "recent").lower()
        if allowed == "popular":
            return "bhz_website_visit_count desc, date_begin asc, id desc"
        return "date_begin asc, id desc"

    @api.model
    def cron_auto_cleanup_events(self):
        now_utc = fields.Datetime.now()
        domain = [
            "|",
            "&",
            ("date_end", "!=", False),
            ("date_end", "<", now_utc),
            "&",
            ("date_end", "=", False),
            ("date_begin", "<", now_utc),
        ]
        events = self.search(domain)
        processed = 0
        tz_name = self.env.user.tz or "UTC"
        tz_env = self.with_context(tz=tz_name)
        now_local = fields.Datetime.context_timestamp(tz_env, now_utc)
        for event in events.sudo():
            deadline = event.date_end or event.date_begin
            if not deadline:
                continue
            deadline_local = fields.Datetime.context_timestamp(tz_env, deadline)
            if deadline_local and now_local and deadline_local > now_local:
                continue
            vals = {}
            if event.show_on_public_agenda:
                vals["show_on_public_agenda"] = False
            if "is_published" in event._fields and event.is_published:
                vals["is_published"] = False
            elif "website_published" in event._fields and event.website_published:
                vals["website_published"] = False
            if "active" in event._fields and event.active:
                vals["active"] = False
            if not vals:
                continue
            event.write(vals)
            processed += 1
        _logger.info("BHZ Event Promo cleanup executed: %s candidates, %s updated", len(events), processed)

    # ------------------------------------------------------------------ Publish
    def _prepare_announced_publication_vals(self):
        vals = {"show_on_public_agenda": True}
        if "website_published" in self._fields:
            vals["website_published"] = True
        if "is_published" in self._fields:
            vals["is_published"] = True
        return vals

    def _get_announced_stage_sequence(self):
        cache_key = "_bhz_announced_stage_sequence"
        cached = getattr(self.env, cache_key, None)
        if cached is not None:
            return cached
        sequence = False
        Stage = self.env["event.stage"].sudo()
        stage_ref = Stage.search(
            [
                "|",
                ("name", "ilike", "announced"),
                ("name", "ilike", "anunciado"),
            ],
            limit=1,
            order="sequence asc, id asc",
        )
        if stage_ref:
            sequence = stage_ref.sequence
        setattr(self.env, cache_key, sequence)
        return sequence

    def _is_announced_stage(self, stage):
        if not stage:
            return False
        stage_names = stage.mapped("name")
        for name in stage_names:
            if not name:
                continue
            lowered = name.lower()
            if "announced" in lowered or "anunciado" in lowered:
                return True
        threshold = self._get_announced_stage_sequence()
        if threshold is False:
            return False
        for stage_item in stage:
            sequence = stage_item.sequence
            if sequence is None:
                continue
            if sequence >= threshold:
                return True
        return False

    def _publish_announced_events(self, events):
        if not events:
            return
        vals = self._prepare_announced_publication_vals()
        events.with_context(_bhz_skip_announced_auto_publish=True).write(vals)
        self._log_announced_publication(events, source="recovery")

    def _log_announced_publication(self, events, stage=None, source="auto_publish"):
        if not events:
            return
        if stage is None:
            stage = events.mapped("stage_id")
        stage_names = ", ".join(filter(None, stage.mapped("name"))) if stage else ""
        _logger.info(
            "BHZ Event Promo auto-publish via %s (stages=%s, event_ids=%s)",
            source,
            stage_names or "?",
            events.ids,
        )

    @api.model_create_multi
    def create(self, vals_list):
        stage_model = self.env["event.stage"]
        for vals in vals_list:
            self._sync_cover_images(vals)
            stage_id = vals.get("stage_id")
            if stage_id:
                stage = stage_model.browse(stage_id)
                if self._is_announced_stage(stage):
                    vals.update(self._prepare_announced_publication_vals())
        records = super().create(vals_list)
        records._propagate_promo_to_standard()
        announced_records = records.filtered(lambda ev: self._is_announced_stage(ev.stage_id))
        if announced_records:
            self._log_announced_publication(announced_records, source="create")
        non_compliant = announced_records.filtered(
            lambda ev: not ev.show_on_public_agenda
            or ("website_published" in ev._fields and not getattr(ev, "website_published"))
            or ("is_published" in ev._fields and not getattr(ev, "is_published"))
        )
        if non_compliant:
            self._publish_announced_events(non_compliant)
        return records

    def write(self, vals):
        if self.env.context.get("_bhz_skip_announced_auto_publish"):
            return super().write(vals)

        vals_to_write = dict(vals)
        if not self.env.context.get("_bhz_skip_promo_sync"):
            self._sync_cover_images(vals_to_write)
        publish_stage = False
        if "stage_id" in vals_to_write and vals_to_write.get("stage_id"):
            stage = self.env["event.stage"].browse(vals_to_write["stage_id"])
            if self._is_announced_stage(stage):
                vals_to_write.update(self._prepare_announced_publication_vals())
                publish_stage = stage
        result = super().write(vals_to_write)
        if not self.env.context.get("_bhz_skip_promo_sync"):
            self._propagate_promo_to_standard()
        if publish_stage:
            self._log_announced_publication(self, stage=publish_stage, source="write")
        return result

    # ---------------------------------------------------------- Registration URL
    def _normalize_external_url(self, url):
        if not url:
            return False
        url = url.strip()
        if not url:
            return False
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def _get_external_registration_url(self):
        self.ensure_one()
        return self._normalize_external_url(self.registration_external_url)

    def _sync_cover_images(self, vals):
        """Copy promo cover image into standard fields for generic snippets."""
        promo = vals.get("promo_cover_image")
        if not promo:
            return
        for field_name in ("image_1920", "cover_image"):
            if field_name in self._fields and field_name not in vals:
                vals[field_name] = promo

    def _propagate_promo_to_standard(self):
        """Ensure existing records without image get promo cover pushed to defaults."""
        if not self:
            return
        for record in self:
            if not record.promo_cover_image:
                continue
            updates = {}
            for field_name in ("image_1920", "cover_image"):
                if field_name in record._fields and not getattr(record, field_name):
                    updates[field_name] = record.promo_cover_image
            if updates:
                record.with_context(_bhz_skip_promo_sync=True).write(updates)

    # ---------------------------------------------------------- Datetime helper
    def _get_display_timezone(self):
        website = getattr(request, "website", False)
        # Odoo 19 website does not expose tz; fall back safely.
        if website and hasattr(website, "tz") and website.tz:
            return website.tz
        if website and hasattr(website, "timezone") and website.timezone:
            return website.timezone
        return self.env.context.get("tz") or self.env.user.tz or "UTC"

    def _localize_datetime(self, dt):
        if not dt:
            return False
        tz = self._get_display_timezone()
        return fields.Datetime.context_timestamp(self.with_context(tz=tz), dt)

    def _format_datetime_display(self, dt, fmt="%d/%m/%Y %H:%M"):
        localized = self._localize_datetime(dt)
        return localized.strftime(fmt) if localized else ""

    # ---------------------------------------------------------- API helpers
    @api.model
    def _api_parse_datetime(self, value, tz_name="UTC"):
        if not value:
            return False
        try:
            dt = fields.Datetime.from_string(value)
        except Exception:
            # try raw iso
            dt = datetime.fromisoformat(value)
        if not dt:
            return False
        if not dt.tzinfo:
            try:
                tz = pytz.timezone(tz_name or "UTC")
            except Exception:
                tz = pytz.UTC
            dt = tz.localize(dt)
        return dt.astimezone(pytz.UTC).replace(tzinfo=None)

    @api.model
    def _api_download_image(self, url, timeout=10):
        if not url:
            return False
        parsed = urlparse(url)
        if not parsed.scheme:
            return False
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            content = resp.content
            if len(content) > 5 * 1024 * 1024:
                raise ValueError("Imagem maior que 5MB")
            return base64.b64encode(content)
        except Exception as err:
            _logger.warning("API import: falha ao baixar imagem %s (%s)", url, err)
            return False

    @api.model
    def _api_extract_image(self, payload):
        image_b64 = payload.get("image_base64") or False
        if image_b64:
            try:
                base64.b64decode(image_b64)
                return image_b64
            except Exception:
                raise ValueError("image_base64 inválida")
        image_url = payload.get("image_url")
        if image_url:
            downloaded = self._api_download_image(image_url)
            if downloaded:
                return downloaded.decode() if isinstance(downloaded, bytes) else downloaded
        return False

    @api.model
    def _api_find_category(self, name):
        if not name:
            return False
        Type = self.env["event.type"].sudo()
        rec = Type.search([("name", "=", name)], limit=1)
        if rec:
            return rec.id
        return Type.create({"name": name}).id

    @api.model
    def _api_prepare_vals(self, payload):
        required = ["title", "start_datetime", "external_source", "external_id"]
        for key in required:
            if not payload.get(key):
                raise ValueError(f"Campo obrigatório ausente: {key}")

        timezone = payload.get("timezone") or "UTC"
        date_begin = self._api_parse_datetime(payload.get("start_datetime"), timezone)
        if not date_begin:
            raise ValueError("start_datetime inválido")
        date_end_raw = payload.get("end_datetime")
        date_end = self._api_parse_datetime(date_end_raw, timezone) if date_end_raw else False

        vals = {
            "name": payload.get("title"),
            "date_begin": date_begin,
            "date_end": date_end,
            "promo_short_description": payload.get("short_description"),
            "promo_description_html": payload.get("description_html"),
            "promo_category_id": self._api_find_category(payload.get("category")),
            "producer_name": payload.get("organizer_name"),
            "external_source": payload.get("external_source"),
            "external_id": payload.get("external_id"),
            "external_url": payload.get("external_url"),
            "external_last_sync": fields.Datetime.now(),
            "registration_external_url": payload.get("tickets_url"),
            "show_on_public_agenda": True,
        }
        if payload.get("tickets_url"):
            vals["registration_mode"] = "external"

        if payload.get("website_id"):
            vals["website_id"] = int(payload["website_id"])

        vals["is_featured"] = bool(payload.get("featured"))

        image_val = self._api_extract_image(payload)
        if image_val:
            vals["promo_cover_image"] = image_val

        if payload.get("published"):
            vals.update(self._prepare_announced_publication_vals())

        if payload.get("published"):
            announced_stage = self._get_announced_stage_sequence()
            if announced_stage and "stage_id" in self._fields and not payload.get("stage_id"):
                stage = self.env["event.stage"].sudo().search(
                    [("sequence", ">=", announced_stage)], limit=1, order="sequence asc, id asc"
                )
                if stage:
                    vals["stage_id"] = stage.id

        return vals

    @api.model
    def bhz_api_upsert_event(self, payload):
        """Create/update event based on external_source + external_id."""
        if not isinstance(payload, dict):
            raise ValueError("Payload inválido")
        source = payload.get("external_source")
        ext_id = payload.get("external_id")
        vals = self._api_prepare_vals(payload)
        Event = self.sudo()
        existing = Event.search(
            [("external_source", "=", source), ("external_id", "=", ext_id)],
            limit=1,
        )
        if existing:
            existing.write(vals)
            record = existing
            action = "updated"
        else:
            record = Event.create(vals)
            action = "created"
        _logger.info(
            "API upsert %s event external=%s/%s -> id=%s",
            action,
            source,
            ext_id,
            record.id,
        )
        return record
