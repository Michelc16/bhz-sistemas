# -*- coding: utf-8 -*-
import logging

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

    @api.model
    def guiabh_get_featured_events(self, limit=12):
        """Return events flagged as featured for website snippets."""
        domain = [
            ("show_on_public_agenda", "=", True),
            ("is_featured", "=", True),
        ]

        website = getattr(request, "website", False)
        if website and "website_id" in self._fields:
            domain += ["|", ("website_id", "=", False), ("website_id", "=", website.id)]

        Stage = self.env["event.stage"].sudo() if "stage_id" in self._fields else False
        if Stage:
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

        if "website_published" in self._fields and "is_published" in self._fields:
            domain += [
                "|",
                ("website_published", "=", True),
                ("is_published", "=", True),
            ]
        elif "website_published" in self._fields:
            domain.append(("website_published", "=", True))
        elif "is_published" in self._fields:
            domain.append(("is_published", "=", True))

        return self.sudo().search(domain, limit=limit, order="date_begin asc, id desc")

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
            stage_id = vals.get("stage_id")
            if stage_id:
                stage = stage_model.browse(stage_id)
                if self._is_announced_stage(stage):
                    vals.update(self._prepare_announced_publication_vals())
        records = super().create(vals_list)
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
        publish_stage = False
        if "stage_id" in vals_to_write and vals_to_write.get("stage_id"):
            stage = self.env["event.stage"].browse(vals_to_write["stage_id"])
            if self._is_announced_stage(stage):
                vals_to_write.update(self._prepare_announced_publication_vals())
                publish_stage = stage
        result = super().write(vals_to_write)
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

    # ---------------------------------------------------------- Datetime helper
    def _get_display_timezone(self):
        website = getattr(request, "website", False)
        if website and website.tz:
            return website.tz
        return self.env.context.get("tz") or self.env.user.tz or "UTC"

    def _localize_datetime(self, dt):
        if not dt:
            return False
        tz = self._get_display_timezone()
        return fields.Datetime.context_timestamp(self.with_context(tz=tz), dt)

    def _format_datetime_display(self, dt, fmt="%d/%m/%Y %H:%M"):
        localized = self._localize_datetime(dt)
        return localized.strftime(fmt) if localized else ""
