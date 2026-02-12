# -*- coding: utf-8 -*-

import base64
import html as py_html
import logging
import re
from datetime import datetime, timedelta

import pytz
import requests
from lxml import html

from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class PortalBHCarnavalImportJob(models.Model):
    """Job de importação do PortalBH.

    Motivo: o scraping pode levar vários segundos/minutos e no Odoo.sh a requisição
    do botão pode estourar timeout do proxy, ficando "carregando" no cliente.
    Então rodamos em lotes via cron.
    """

    _name = "bhz.portalbh.carnaval.import.job"
    _description = "Job Importação PortalBH - Carnaval 2026"
    _order = "create_date desc"

    name = fields.Char(default=lambda self: _("Importação PortalBH"), required=True)

    state = fields.Selection(
        [
            ("pending", "Pendente"),
            ("running", "Executando"),
            ("done", "Concluído"),
            ("failed", "Falhou"),
            ("canceled", "Cancelado"),
        ],
        default="pending",
        required=True,
        index=True,
    )

    source_url = fields.Char(
        string="URL base",
        required=True,
        default="https://portalbelohorizonte.com.br/carnaval/2026/programacao/bloco-de-rua",
    )
    max_pages = fields.Integer(string="Máx. páginas", default=50)
    current_page = fields.Integer(string="Página atual", default=1)
    update_existing = fields.Boolean(string="Atualizar existentes", default=True)
    default_duration_hours = fields.Float(string="Duração padrão (h)", default=3.0)

    created_count = fields.Integer(string="Criados", default=0)
    updated_count = fields.Integer(string="Atualizados", default=0)
    skipped_count = fields.Integer(string="Ignorados", default=0)
    error_count = fields.Integer(string="Erros", default=0)

    last_run = fields.Datetime(string="Última execução")
    log = fields.Text(string="Log")

    # Configs de performance/segurança
    pages_per_cron = fields.Integer(string="Páginas por execução", default=2)
    request_timeout_connect = fields.Integer(string="Timeout conexão (s)", default=5)
    request_timeout_read = fields.Integer(string="Timeout leitura (s)", default=20)
    image_max_bytes = fields.Integer(string="Tamanho máximo imagem (bytes)", default=2_000_000)

    # ---------------------------------------------------------------------
    # UI actions
    # ---------------------------------------------------------------------
    def action_enqueue(self):
        for job in self:
            if job.state in ("done", "failed", "canceled"):
                continue
            job.write({"state": "pending"})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Importação iniciada"),
                "message": _(
                    "Job criado e agendado. A importação roda em background. Abra este registro para acompanhar o progresso."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_run_now(self):
        """Permite rodar um lote manualmente."""
        self.ensure_one()
        self._run_batch()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_cancel(self):
        self.write({"state": "canceled"})

    # ---------------------------------------------------------------------
    # Cron entrypoint
    # ---------------------------------------------------------------------
    @api.model
    def _cron_run_pending_jobs(self, limit=3):
        jobs = self.search([("state", "in", ("pending", "running"))], limit=limit)
        for job in jobs:
            try:
                job._run_batch()
            except Exception as err:
                _logger.exception("[PortalBH Carnaval] job %s falhou: %s", job.id, err)
                job._append_log(f"ERRO FATAL: {err}")
                job.state = "failed"

    # ---------------------------------------------------------------------
    # Core runner
    # ---------------------------------------------------------------------
    def _run_batch(self):
        self.ensure_one()
        if self.state in ("done", "failed", "canceled"):
            return

        self.state = "running"
        self.last_run = fields.Datetime.now()

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "BHZ Sistemas (Odoo) - bhz_event_promo importer",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

        page_from = max(1, int(self.current_page or 1))
        page_to = min(int(self.max_pages or 1), page_from + max(1, int(self.pages_per_cron or 1)) - 1)

        any_found = False
        for page in range(page_from, page_to + 1):
            links = self._collect_links_for_page(session, page)
            if not links:
                # Se não tem links numa página, assume fim
                self._append_log(f"Página {page}: nenhum link encontrado (fim)")
                if not any_found:
                    # se já no primeiro page do lote não teve nada, conclui
                    self.state = "done"
                self.current_page = page + 1
                break

            any_found = True
            self._append_log(f"Página {page}: {len(links)} links")
            self._import_links(session, links)
            self.current_page = page + 1

        # Se passou do máximo, conclui
        if int(self.current_page or 1) > int(self.max_pages or 1):
            self.state = "done"

    def _import_links(self, session, links):
        Event = self.env["event.event"].sudo()

        for url, card_hint in links:
            try:
                payload = self._parse_desfile_detail(session, url, card_hint=card_hint)
                if not payload:
                    self.skipped_count += 1
                    continue

                existing = Event.search(
                    [
                        ("external_source", "=", payload["external_source"]),
                        ("external_id", "=", payload["external_id"]),
                    ],
                    limit=1,
                )
                if existing:
                    if self.update_existing:
                        existing.write(payload["vals"])
                        self.updated_count += 1
                    else:
                        self.skipped_count += 1
                else:
                    Event.create(payload["vals"])
                    self.created_count += 1
            except Exception as err:
                self.error_count += 1
                _logger.exception("[PortalBH Carnaval] erro ao importar %s: %s", url, err)
                self._append_log(f"Erro ao importar {url}: {err}")

    # ---------------------------------------------------------------------
    # Scraper helpers
    # ---------------------------------------------------------------------
    def _timeout(self):
        return (int(self.request_timeout_connect or 5), int(self.request_timeout_read or 20))

    def _collect_links_for_page(self, session, page):
        base = (self.source_url or "").strip()
        if not base:
            return []

        url = base if page == 1 else f"{base}?page={page}"
        resp = session.get(url, timeout=self._timeout())
        if resp.status_code >= 400:
            self._append_log(f"Página {page}: HTTP {resp.status_code}")
            return []

        doc = html.fromstring(resp.content)
        doc.make_links_absolute(url)

        anchors = doc.xpath("//a[contains(@href, '/desfile/')]")
        found = []
        seen = set()
        for a in anchors:
            href = (a.get("href") or "").strip()
            if not href or "/desfile/" not in href:
                continue
            if "api.whatsapp.com" in href or "whatsapp" in href:
                continue
            href = href.split("#", 1)[0]
            if href in seen:
                continue
            seen.add(href)

            card = a.getparent()
            for _ in range(6):
                if card is None:
                    break
                text = " ".join((card.text_content() or "").split())
                if re.search(r"\d{2}/\d{2}/\d{4}", text) and re.search(r"\d{2}:\d{2}", text):
                    break
                card = card.getparent()
            hint = self._parse_card_hint(card.text_content() if card is not None else "")
            found.append((href, hint))

        return found

    def _parse_card_hint(self, text):
        text = " ".join((text or "").split())
        date_m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        time_m = re.search(r"(\d{2}:\d{2})", text)

        bairro = False
        m = re.search(r"Bloco\s+de\s+Rua\s+([A-Za-zÀ-ÿ0-9\-\s]+)$", text)
        if m:
            bairro = (m.group(1) or "").strip() or False

        return {
            "date": date_m.group(1) if date_m else False,
            "time": time_m.group(1) if time_m else False,
            "neighborhood": bairro,
        }

    def _parse_desfile_detail(self, session, url, card_hint=None):
        resp = session.get(url, timeout=self._timeout())
        if resp.status_code >= 400:
            return False

        doc = html.fromstring(resp.content)
        doc.make_links_absolute(url)

        title = self._first_text(doc.xpath("//h1"))
        if not title:
            title = self._first_text(doc.xpath("//*[self::h1 or self::h2][1]"))
        title = (title or "").strip()
        if not title:
            return False

        external_id = self._extract_external_id(url)
        if not external_id:
            return False

        page_text = "\n".join([line.strip() for line in doc.text_content().splitlines() if line.strip()])
        description = self._extract_between(page_text, "Descrição", "Localização")
        if not description:
            description = self._extract_between(page_text, "Descrição", "Data")

        date_begin = self._extract_datetime(page_text, card_hint=card_hint)
        if not date_begin:
            return False
        date_end = date_begin + timedelta(hours=float(self.default_duration_hours or 3.0))

        entrada = self._extract_field(page_text, "Entrada")
        ticket_kind = "unknown"
        if entrada:
            up = entrada.upper()
            if "GRATUIT" in up or "ENTRADA FRANCA" in up:
                ticket_kind = "free"
            elif re.search(r"R\$\s*\d", entrada):
                ticket_kind = "paid"

        locais_block = self._extract_between(page_text, "Locais", "Entrada")
        conc, disp = self._extract_conc_disp(locais_block)

        neighborhood = False
        if card_hint and card_hint.get("neighborhood"):
            neighborhood = card_hint.get("neighborhood")
        else:
            neighborhood = self._guess_neighborhood(conc) or self._guess_neighborhood(disp)

        image_b64 = False
        image_url = self._extract_meta_image(doc) or self._extract_first_reasonable_image(doc)
        if image_url:
            image_b64 = self._download_image_base64(session, image_url)

        venue_partner = self._get_or_create_venue(conc or disp) if (conc or disp) else self.env["res.partner"].browse()

        vals = {
            "name": title,
            "date_begin": date_begin,
            "date_end": date_end,
            "registration_mode": "disclosure_only",
            "registration_button_label": "Ver detalhes",
            "registration_external_url": False,
            "promo_short_description": (description[:180] if description else False),
            "promo_description_html": self._to_html_paragraphs(description),
            "ticket_kind": ticket_kind,
            "neighborhood": neighborhood or False,
            "venue_partner_id": venue_partner.id if venue_partner else False,
            "is_third_party": True,
            "third_party_name": "Portal Belo Horizonte - Carnaval 2026",
            "external_source": "portalbh_carnaval_2026",
            "external_id": external_id,
            "external_url": url,
            "external_last_sync": fields.Datetime.now(),
            "show_on_public_agenda": True,
        }
        if image_b64:
            vals["promo_cover_image"] = image_b64

        return {"external_source": vals["external_source"], "external_id": vals["external_id"], "vals": vals}

    # ---------------------------------------------------------------------
    # Parsing helpers (copiados do wizard original, com pequenos reforços)
    # ---------------------------------------------------------------------
    def _extract_external_id(self, url):
        m = re.search(r"-(\d+)$", (url or "").rstrip("/"))
        return m.group(1) if m else False

    def _extract_between(self, text, start_label, end_label):
        if not text:
            return ""
        pattern = rf"{re.escape(start_label)}\s*(.+?)\s*{re.escape(end_label)}"
        m = re.search(pattern, text, flags=re.S | re.I)
        if not m:
            return ""
        chunk = (m.group(1) or "").strip()
        chunk = re.sub(r"Compartilhar\s+por:\s*.*", "", chunk, flags=re.I)
        chunk = re.sub(r"Quer\s+saber\s+a\s+melhor\s+forma\s+de\s+chegar.*", "", chunk, flags=re.I | re.S)
        return chunk.strip()

    def _extract_field(self, text, label):
        if not text:
            return ""
        m = re.search(rf"{re.escape(label)}\s*\n\s*([^\n]+)", text, flags=re.I)
        return (m.group(1) or "").strip() if m else ""

    def _extract_conc_disp(self, locais_text):
        if not locais_text:
            return (False, False)
        locais_text = "\n".join([l.strip() for l in (locais_text or "").splitlines() if l.strip()])
        conc = disp = False
        m1 = re.search(r"Concentraç[aã]o:\s*\n?\s*([^\n]+)", locais_text, flags=re.I)
        m2 = re.search(r"Dispers[aã]o:\s*\n?\s*([^\n]+)", locais_text, flags=re.I)
        if m1:
            conc = (m1.group(1) or "").strip()
        if m2:
            disp = (m2.group(1) or "").strip()
        return (conc, disp)

    def _guess_neighborhood(self, addr):
        if not addr:
            return False
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        if len(parts) >= 3:
            return parts[-1]
        return False

    def _extract_datetime(self, page_text, card_hint=None):
        m = re.search(r"Data\s*\n\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}:\d{2})", page_text)
        date_s = time_s = False
        if m:
            date_s, time_s = m.group(1), m.group(2)
        elif card_hint and card_hint.get("date") and card_hint.get("time"):
            date_s, time_s = card_hint.get("date"), card_hint.get("time")
        if not (date_s and time_s):
            return False

        try:
            dt_local = datetime.strptime(f"{date_s} {time_s}", "%d/%m/%Y %H:%M")
        except Exception:
            return False

        tzname = self.env.user.tz or "America/Sao_Paulo"
        try:
            tz = pytz.timezone(tzname)
        except Exception:
            tz = pytz.timezone("America/Sao_Paulo")

        dt_aware = tz.localize(dt_local)
        dt_utc = dt_aware.astimezone(pytz.UTC).replace(tzinfo=None)
        return dt_utc

    def _to_html_paragraphs(self, text):
        if not text:
            return False
        lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
        if not lines:
            return False
        return "".join([f"<p>{py_html.escape(l)}</p>" for l in lines])

    def _extract_meta_image(self, doc):
        for xp in [
            "//meta[@property='og:image']/@content",
            "//meta[@name='twitter:image']/@content",
            "//meta[@name='image']/@content",
        ]:
            val = self._first_text(doc.xpath(xp))
            if val:
                return val.strip()
        return False

    def _extract_first_reasonable_image(self, doc):
        imgs = doc.xpath("//img/@src")
        for src in imgs:
            src = (src or "").strip()
            if not src:
                continue
            low = src.lower()
            if any(x in low for x in ["logo", "vlibras", "icon", "sprite", "whatsapp"]):
                continue
            if low.endswith((".png", ".jpg", ".jpeg", ".webp")):
                return src
        return False

    def _download_image_base64(self, session, image_url):
        try:
            resp = session.get(image_url, timeout=self._timeout(), stream=True)
            if resp.status_code >= 400:
                return False
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "image" not in content_type and not re.search(r"\.(png|jpg|jpeg|webp)(\?|$)", image_url, re.I):
                return False

            # Evitar baixar imagens gigantes
            length = resp.headers.get("Content-Length")
            if length and int(length) > int(self.image_max_bytes or 2_000_000):
                return False
            content = resp.content
            if content and len(content) > int(self.image_max_bytes or 2_000_000):
                return False
            return base64.b64encode(content)
        except Exception:
            return False

    def _get_or_create_venue(self, name):
        if not name:
            return self.env["res.partner"].browse()
        clean = (name or "").strip()
        Partner = self.env["res.partner"].sudo()
        venue = Partner.search([("name", "=", clean)], limit=1)
        if not venue:
            venue = Partner.create({"name": clean, "company_type": "company"})
        return venue

    def _first_text(self, items):
        if not items:
            return False
        val = items[0]
        if isinstance(val, str):
            return val
        try:
            return val.text_content()
        except Exception:
            return str(val)

    # ---------------------------------------------------------------------
    # Logging
    # ---------------------------------------------------------------------
    def _append_log(self, line):
        self.ensure_one()
        prefix = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_line = f"[{prefix}] {line}"
        self.log = (self.log or "") + ("\n" if self.log else "") + new_line
