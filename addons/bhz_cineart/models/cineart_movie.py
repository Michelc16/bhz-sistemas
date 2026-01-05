# -*- coding: utf-8 -*-
import json
import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from lxml import html

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CineartMovie(models.Model):
    _name = "guiabh.cineart.movie"
    _description = "Cineart - Filmes"
    _order = "category, name"

    BASE_URL = "https://cineart.com.br/"
    CINEART_ROUTES = {
        "now": "https://cineart.com.br/em-cartaz",
        "premiere": "https://cineart.com.br/estreias",
        "soon": "https://cineart.com.br/em-breve",
    }
    MIN_VALID_ITEMS = 5

    name = fields.Char(string="Título", required=True, index=True)
    category = fields.Selection(
        [
            ("now", "Em cartaz"),
            ("soon", "Em breve"),
            ("premiere", "Estreias da semana"),
        ],
        string="Categoria",
        required=True,
        index=True,
        default="now",
    )
    genre = fields.Char(string="Gênero")
    age_rating = fields.Char(string="Classificação indicativa")
    release_date = fields.Char(string="Data de estreia", help="Data exibida no site (quando houver).")
    cineart_url = fields.Char(string="Link no site Cineart")
    poster_url = fields.Char(string="URL externa do cartaz")
    active = fields.Boolean(string="Ativo", default=True)
    poster_image = fields.Image(string="Cartaz (imagem)", max_width=1024, max_height=1024)
    last_sync = fields.Datetime(string="Última sincronização", readonly=True)

    _sql_constraints = [
        ("cineart_url_unique", "unique(cineart_url)", "Já existe um filme com este link do Cineart."),
    ]

    def action_open_cineart(self):
        self.ensure_one()
        if not self.cineart_url:
            raise UserError(_("Este filme não possui URL do Cineart."))
        return {
            "type": "ir.actions.act_url",
            "url": self.cineart_url,
            "target": "new",
        }

    def action_sync_now(self):
        return self.env["guiabh.cineart.movie"].action_sync_all_now()

    @api.model
    def guiabh_get_movies(self, categories=None, limit=12):
        domain = [("active", "=", True)]
        if categories:
            valid_codes = {code for code, _label in self._fields["category"].selection}
            filtered = [code for code in categories if code in valid_codes]
            if filtered:
                domain.append(("category", "in", filtered))
        return self.search(domain, order="category asc, name asc, id desc", limit=limit)

    @api.model
    def action_sync_all_now(self):
        results = self.sudo()._run_sync(raise_on_error=True)
        return self._build_sync_notification(results, _("Sincronização concluída"))

    def _build_sync_notification(self, results, title):
        lines = []
        for entry in results:
            if entry.get("valid"):
                lines.append(
                    _("%(cat)s: %(count)s itens (%(created)s novos, %(updated)s atualizados, %(inactive)s inativados)")
                    % entry
                )
            else:
                lines.append(_("%(cat)s: sem mudanças (falha ou poucos itens)") % entry)
        if not lines:
            lines.append(_("Sincronização executada."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": "\n".join(lines),
                "type": "success",
                "sticky": False,
            },
        }

    # =========================
    # SINCRONIZAÇÃO
    # =========================

    @api.model
    def cron_sync_all(self):
        results = self.sudo()._run_sync(raise_on_error=False)
        for entry in results:
            if entry["valid"]:
                _logger.info(
                    "Cineart cron sync OK: categoria=%(cat)s total=%(count)s criados=%(created)s atualizados=%(updated)s inativados=%(inactive)s",
                    entry,
                )
            else:
                _logger.warning("Cineart cron sync falhou/parcial para %(cat)s (itens=%(count)s)", entry)
        return results

    @api.model
    def sync_category(self, category):
        url = self.CINEART_ROUTES.get(category)
        if not url:
            raise UserError(_("Categoria inválida: %s") % category)
        return self._sync_category(url, category, raise_on_error=True)

    @api.model
    def _sync_category(self, url, category, raise_on_error=False):
        if not url:
            msg = _("Categoria inválida: %s") % category
            _logger.error("Cineart sync aborted: %s", msg)
            if raise_on_error:
                raise UserError(msg)
            return {"valid": False, "count": 0, "created": 0, "updated": 0, "inactivated": 0}

        response = None
        last_error = None
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": url,
        }
        for candidate in self._iter_fallback_urls(url):
            try:
                response = requests.get(candidate, timeout=(10, 30), headers=headers, allow_redirects=True)
                response.raise_for_status()
                _logger.info("Cineart sync request OK: %s", candidate)
                break
            except Exception as err:  # pylint: disable=broad-except
                last_error = err
                _logger.warning("Cineart sync HTTP error (%s) em %s: %s", category, candidate, err)
        if not response:
            _logger.exception("Cineart sync HTTP error (%s): %s", category, last_error)
            if raise_on_error:
                raise UserError(_("Falha ao acessar %(url)s: %(msg)s") % {"url": url, "msg": last_error})
            return {"valid": False, "count": 0, "created": 0, "updated": 0, "inactivated": 0}

        try:
            doc = html.fromstring(response.content)
            items = self._parse_movies(doc, base_url=self.BASE_URL)
        except Exception as err:  # pylint: disable=broad-except
            _logger.exception("Cineart parse error (%s): %s", category, err)
            if raise_on_error:
                raise UserError(_("Falha ao interpretar os dados de %(cat)s: %(msg)s") % {"cat": category, "msg": err})
            return {"valid": False, "count": 0, "created": 0, "updated": 0, "inactivated": 0}

        if not items or len(items) < self.MIN_VALID_ITEMS:
            _logger.warning(
                "Cineart sync aborted (%s): encontrou %s itens (< %s)",
                category,
                len(items) if items else 0,
                self.MIN_VALID_ITEMS,
            )
            return {"valid": False, "count": len(items) if items else 0, "created": 0, "updated": 0, "inactivated": 0}

        existing = self.search([("category", "=", category)])
        existing_by_url = {}
        for rec in existing:
            norm_url = self._normalize_cineart_url(rec.cineart_url)
            if norm_url and rec.cineart_url != norm_url:
                rec.with_context(active_test=False).write({"cineart_url": norm_url})
            if norm_url:
                existing_by_url[norm_url.lower()] = rec
        seen = set()
        now = fields.Datetime.now()
        created = updated = 0

        for item in items:
            cineart_url = self._normalize_cineart_url(item.get("cineart_url")) or self._build_fallback_url(
                category, item.get("name")
            )
            if not cineart_url:
                continue
            key = cineart_url.lower()
            seen.add(key)
            vals = {
                "name": item.get("name"),
                "category": category,
                "genre": item.get("genre"),
                "age_rating": item.get("age_rating"),
                "release_date": item.get("release_date"),
                "cineart_url": cineart_url,
                "poster_url": item.get("poster_url"),
                "active": True,
                "last_sync": now,
            }
            rec = existing_by_url.get(key)
            if rec:
                rec.write(vals)
                updated += 1
            else:
                rec = self.create(vals)
                existing_by_url[key] = rec
                created += 1
            self._try_fetch_image(rec)

        inactivated = 0
        for rec in existing:
            norm_url = self._normalize_cineart_url(rec.cineart_url)
            if norm_url and norm_url.lower() not in seen:
                rec.active = False
                inactivated += 1

        _logger.info(
            "Cineart sync DONE: category=%s total=%s created=%s updated=%s inactivated=%s",
            category,
            len(items),
            created,
            updated,
            inactivated,
        )
        return {
            "valid": True,
            "count": len(items),
            "created": created,
            "updated": updated,
            "inactivated": inactivated,
        }

    def _run_sync(self, raise_on_error=False):
        categories = [
            ("now", _("Em cartaz")),
            ("premiere", _("Estreias da semana")),
            ("soon", _("Em breve")),
        ]
        results = []
        for code, label in categories:
            url = self.CINEART_ROUTES.get(code)
            try:
                data = self._sync_category(url, code, raise_on_error=raise_on_error) or {}
            except UserError:
                raise
            except Exception as err:  # pylint: disable=broad-except
                _logger.exception("Erro inesperado ao sincronizar categoria %s", code)
                if raise_on_error:
                    raise UserError(_("Falha inesperada ao sincronizar %(cat)s: %(msg)s") % {"cat": label, "msg": err})
                data = {"valid": False, "count": 0, "created": 0, "updated": 0, "inactivated": 0}

            results.append(
                {
                    "cat": label,
                    "valid": data.get("valid", False),
                    "count": data.get("count", 0),
                    "created": data.get("created", 0),
                    "updated": data.get("updated", 0),
                    "inactive": data.get("inactivated", 0),
                }
            )
        return results

    @api.model
    def _parse_movies(self, doc, base_url):
        movies = self._parse_movies_from_dom(doc, base_url)
        _logger.info("Cineart parser DOM aceitou %s itens", len(movies))
        if len(movies) >= self.MIN_VALID_ITEMS:
            return movies
        json_movies = self._parse_movies_from_json(doc, base_url)
        if json_movies:
            _logger.info("Cineart parser JSON aceitou %s itens", len(json_movies))
            return json_movies
        return movies

    def _parse_movies_from_dom(self, doc, base_url):
        results = []
        seen_urls = set()
        images = doc.xpath("//img")

        for img in images:
            poster_raw = img.get("src") or img.get("data-src") or ""
            if not poster_raw:
                continue
            poster_low = poster_raw.lower()
            if any(token in poster_low for token in ("logo", "icon", "sprite", "placeholder")):
                continue

            container = self._get_card_container(img)
            movie = self._extract_movie_data(container, img, base_url)
            if not movie:
                continue
            key = (movie.get("cineart_url") or movie.get("name", "")).lower()
            if key and key in seen_urls:
                continue
            seen_urls.add(key)
            results.append(movie)

        _logger.info("Cineart parser DOM examinou %s imagens e encontrou %s candidatos", len(images), len(results))
        return results

    def _parse_movies_from_json(self, doc, base_url):
        scripts = doc.xpath("//script[contains(@type,'json')]/text()") + doc.xpath("//script[@id='__NEXT_DATA__']/text()")
        movies = []
        seen = set()
        for script_text in scripts:
            try:
                data = json.loads(script_text)
            except Exception:  # pylint: disable=broad-except
                continue
            extracted = self._extract_from_json_blob(data, base_url)
            for movie in extracted:
                key = (movie.get("cineart_url") or movie.get("name", "")).lower()
                if key and key in seen:
                    continue
                seen.add(key)
                movies.append(movie)
        return movies

    def _extract_from_json_blob(self, data, base_url):
        results = []
        if isinstance(data, dict):
            if data.get("@type") in {"Movie", "VideoObject"}:
                movie = {
                    "name": data.get("name"),
                    "genre": ", ".join(data.get("genre")) if isinstance(data.get("genre"), list) else data.get("genre"),
                    "age_rating": data.get("contentRating"),
                    "release_date": data.get("datePublished") or data.get("dateCreated"),
                    "cineart_url": self._normalize_cineart_url(data.get("url")),
                    "poster_url": self._safe_url(data.get("image"), base_url),
                }
                if movie["name"]:
                    results.append(movie)
            for value in data.values():
                results.extend(self._extract_from_json_blob(value, base_url))
        elif isinstance(data, list):
            for item in data:
                results.extend(self._extract_from_json_blob(item, base_url))
        return results

    def _safe_url(self, value, base_url):
        if not value:
            return False
        if isinstance(value, dict):
            value = value.get("url")
        if isinstance(value, list):
            value = value[0]
        value = (value or "").strip()
        if not value:
            return False
        return urljoin(base_url, value)

    def _get_card_container(self, node):
        for ancestor in node.iterancestors():
            if ancestor.tag in ("article", "div", "li", "section"):
                classes = (ancestor.get("class") or "").lower()
                if any(keyword in classes for keyword in ("filme", "movie", "card", "item", "catalogo", "poster")):
                    return ancestor
        parent = node.getparent()
        return parent if parent is not None else node

    def _extract_movie_data(self, container, img, base_url):
        if container is None:
            return None
        poster_url = img.get("src") or img.get("data-src") or ""
        poster_url = poster_url.strip()
        poster_url = urljoin(base_url, poster_url) if poster_url else False

        texts = [self._clean_text(text) for text in container.xpath(".//text()")]
        texts = [text for text in texts if text]
        text_block = " ".join(texts)
        text_block_lower = text_block.lower()
        text_block_upper = text_block.upper()

        title = self._extract_title(container, texts)
        if not title:
            return None

        genre = ""
        for option in ["Ação", "Animação", "Infantil", "Terror", "Suspense", "Drama", "Comédia", "Aventura", "Romance"]:
            if option.lower() in text_block_lower:
                genre = option
                break

        age_rating = ""
        match = re.search(r"\b(10|12|14|16|18)\b", text_block)
        if match:
            age_rating = match.group(1)
        elif re.search(r"\bL\b", text_block_upper):
            age_rating = "L"

        release_date = ""
        release_match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", text_block)
        if release_match:
            release_date = release_match.group(1)

        href = ""
        anchor = container.xpath(".//a[@href][1]")
        if anchor:
            href = anchor[0].get("href") or ""
        cineart_url = self._normalize_cineart_url(urljoin(base_url, href))

        return {
            "name": title,
            "genre": genre,
            "age_rating": age_rating,
            "release_date": release_date,
            "cineart_url": cineart_url,
            "poster_url": poster_url,
        }

    def _extract_title(self, container, texts):
        title_nodes = container.xpath(
            ".//h1|.//h2|.//h3|.//h4|.//h5|.//h6|.//*[contains(@class,'title')]|.//*[contains(@class,'titulo')]"
        )
        for node in title_nodes:
            value = self._clean_text(" ".join(node.xpath(".//text()")))
            if len(value) > 2:
                return value
        for text in texts:
            if len(text) > 2:
                return text
        return ""

    def _clean_text(self, value):
        return " ".join((value or "").split()).strip()

    def _try_fetch_image(self, rec):
        if not rec.poster_url:
            return
        try:
            response = requests.get(rec.poster_url, timeout=30)
            response.raise_for_status()
            rec.poster_image = response.content
        except Exception as err:  # pylint: disable=broad-except
            _logger.warning("Falha ao baixar poster %s: %s", rec.poster_url, err)

    def _normalize_cineart_url(self, url):
        url = (url or "").strip()
        if not url:
            return False
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http"):
            url = urljoin(self.BASE_URL, url.lstrip("/"))
        url = url.replace("http://", "https://", 1)
        parsed = urlparse(url)
        host = parsed.netloc.replace("www.", "")
        netloc = host or parsed.netloc
        canonical = urlunparse((parsed.scheme or "https", netloc, parsed.path or "", "", parsed.query or "", ""))
        if "cineart.com.br" not in canonical:
            return False
        return canonical

    def _build_fallback_url(self, category, name):
        name = (name or "").strip()
        if not name:
            return False
        slug = self._slugify(name)
        return f"https://cineart.com.br/{category or 'filme'}/{slug}"

    def _slugify(self, value):
        slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
        return slug or "filme"

    def _iter_fallback_urls(self, url):
        url = (url or "").strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url.lstrip("/")
        parsed = urlparse(url)
        host = parsed.netloc.replace("www.", "")
        candidates = [host, f"www.{host}"] if host else [parsed.netloc]
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            yield urlunparse((parsed.scheme or "https", candidate, parsed.path or "", "", parsed.query or "", parsed.fragment or ""))
