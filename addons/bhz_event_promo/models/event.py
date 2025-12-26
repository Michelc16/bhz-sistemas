# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EventEvent(models.Model):
    _inherit = "event.event"

    is_third_party = fields.Boolean(string="Evento de terceiro", default=False)
    third_party_name = fields.Char(string="Organizador / Fonte (texto livre)")
    third_party_partner_id = fields.Many2one("res.partner", string="Organizador (contato)")
    promo_html_description = fields.Html(
        string="Descrição do evento (site)",
        sanitize=True,
        translate=True,
        help="Descrição rica exibida na página pública do evento.",
    )

    # Modo do botão: interno (Odoo) ou externo (link)
    registration_mode = fields.Selection(
        [
            ("internal", "Inscrição/Venda pelo meu site (Odoo)"),
            ("external", "Redirecionar para link externo"),
            ("promo", "Divulgação (sem link)"),
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
    promo_show_button = fields.Boolean(
        string="Mostrar botão na divulgação",
        default=False,
        help="Quando em modo divulgação, exibe um botão informativo mesmo sem link.",
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
        self._migrate_promo_html_description()

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

    def _migrate_promo_html_description(self):
        columns = self._existing_columns()
        target_col = "promo_html_description"
        if target_col not in columns:
            return

        for source in (
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

    @api.model
    def cron_auto_cleanup_events(self):
        now = fields.Datetime.now()
        domain = [
            ("auto_remove_after_event", "!=", "none"),
            ("date_end", "<", now),
        ]
        events = self.search(domain)
        for event in events.sudo():
            if event.auto_remove_after_event == "unpublish":
                vals = {"show_on_public_agenda": False}
                if "is_published" in event._fields:
                    vals["is_published"] = False
                if "website_published" in event._fields:
                    vals["website_published"] = False
                event.write(vals)
            elif event.auto_remove_after_event == "delete":
                event.unlink()
