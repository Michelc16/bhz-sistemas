# -*- coding: utf-8 -*-
import base64
import logging
import re
import html as py_html
from datetime import datetime, timedelta
import pytz
import requests
from lxml import html

from odoo import _, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class PortalBHCarnavalImportWizard(models.TransientModel):
    """Importa Blocos de Rua do Portal Oficial de Belo Horizonte (Carnaval 2026).

    Fonte: https://portalbelohorizonte.com.br/carnaval/2026/programacao/bloco-de-rua
    """

    _name = "bhz.portalbh.carnaval.import.wizard"
    _description = "Importador PortalBH - Carnaval 2026 (Blocos de Rua)"

    source_url = fields.Char(
        string="URL base",
        default="https://portalbelohorizonte.com.br/carnaval/2026/programacao/bloco-de-rua",
        required=True,
    )
    max_pages = fields.Integer(string="Máx. páginas", default=50)
    update_existing = fields.Boolean(string="Atualizar existentes", default=True)
    default_duration_hours = fields.Float(string="Duração padrão (h)", default=3.0)

    def action_import_portalbh(self):
        self.ensure_one()

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "BHZ Sistemas (Odoo) - bhz_event_promo importer",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

        links = self._collect_desfile_links(session)
        if not links:
            raise UserError(_("Não encontrei nenhum bloco para importar. Verifique a URL e tente novamente."))

        Event = self.env["event.event"].sudo()

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for url, card_hint in links:
            try:
                payload = self._parse_desfile_detail(session, url, card_hint=card_hint)
                if not payload:
                    skipped += 1
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
                        updated += 1
                    else:
                        skipped += 1
                else:
                    Event.create(payload["vals"])
                    created += 1
            except Exception as err:
                errors += 1
                _logger.exception("[PortalBH Carnaval] erro ao importar %s: %s", url, err)

        msg = _(
            "Importação concluída. Criados: %(c)s | Atualizados: %(u)s | Ignorados: %(s)s | Erros: %(e)s",
            c=created,
            u=updated,
            s=skipped,
            e=errors,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Importação concluída'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }

    # ---------------------------------------------------------------------
    # Scraper
    # ---------------------------------------------------------------------
    def _collect_desfile_links(self, session):
        """Varre a listagem paginada e devolve [(url, card_hint_dict), ...]."""

        base = (self.source_url or "").strip()
        if not base:
            return []

        seen = set()
        found = []
        for page in range(1, max(1, int(self.max_pages or 1)) + 1):
            url = base if page == 1 else f"{base}?page={page}"
            resp = session.get(url, timeout=30)
            if resp.status_code >= 400:
                _logger.warning("[PortalBH Carnaval] página %s retornou %s", url, resp.status_code)
                break

            doc = html.fromstring(resp.content)
            doc.make_links_absolute(url)

            # Heurística: anchors com '/desfile/' no href
            anchors = doc.xpath("//a[contains(@href, '/desfile/')]")
            page_links = 0

            for a in anchors:
                href = (a.get("href") or "").strip()
                if not href or "/desfile/" not in href:
                    continue
                # Evitar links de share/whatsapp etc.
                if "api.whatsapp.com" in href or "whatsapp" in href:
                    continue

                href = href.split("#", 1)[0]
                if href in seen:
                    continue
                seen.add(href)
                page_links += 1

                # Captura pistas do card (bairro/endereço/dia/hora) se estiverem no mesmo bloco
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

            # Se uma página não trouxe nenhum link novo, encerra
            if page_links == 0:
                break

        return found

    def _parse_card_hint(self, text):
        """Extrai informações básicas do card da listagem (quando disponíveis)."""
        text = " ".join((text or "").split())
        date_m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        time_m = re.search(r"(\d{2}:\d{2})", text)

        # Bairro costuma aparecer como última linha do card, mas é heurístico.
        # Padrão: ... Bloco de Rua <bairro>
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
        resp = session.get(url, timeout=30)
        if resp.status_code >= 400:
            return False

        doc = html.fromstring(resp.content)
        doc.make_links_absolute(url)

        title = self._first_text(doc.xpath("//h1"))
        if not title:
            # fallback
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
            # fallback: tenta entre "Descrição" e "Data"
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

        # Image (nem sempre existe)
        image_b64 = False
        image_url = self._extract_meta_image(doc) or self._extract_first_reasonable_image(doc)
        if image_url:
            image_b64 = self._download_image_base64(session, image_url)

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
            "venue_partner_id": self._get_or_create_venue(conc or disp).id if (conc or disp) else False,
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
    # Parsing helpers
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
        # remove ruídos comuns do portal
        chunk = re.sub(r"Compartilhar\s+por:\s*.*", "", chunk, flags=re.I)
        chunk = re.sub(r"Quer\s+saber\s+a\s+melhor\s+forma\s+de\s+chegar.*", "", chunk, flags=re.I | re.S)
        return chunk.strip()

    def _extract_field(self, text, label):
        if not text:
            return ""
        # label\nvalor\n...
        m = re.search(rf"{re.escape(label)}\s*\n\s*([^\n]+)", text, flags=re.I)
        return (m.group(1) or "").strip() if m else ""

    def _extract_conc_disp(self, locais_text):
        if not locais_text:
            return (False, False)
        locais_text = "\n".join([l.strip() for l in (locais_text or "").splitlines() if l.strip()])
        conc = False
        disp = False
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
        # Heurística simples: "Rua X, 123, Bairro"
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        if len(parts) >= 3:
            return parts[-1]
        return False

    def _extract_datetime(self, page_text, card_hint=None):
        # Preferir o texto do detalhe
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
        safe = "".join([f"<p>{py_html.escape(l)}</p>" for l in lines])
        return safe

    def _extract_meta_image(self, doc):
        # tenta og:image / twitter:image
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
            resp = session.get(image_url, timeout=30)
            if resp.status_code >= 400:
                return False
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "image" not in content_type and not re.search(r"\.(png|jpg|jpeg|webp)(\?|$)", image_url, re.I):
                return False
            return base64.b64encode(resp.content)
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
