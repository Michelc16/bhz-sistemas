# -*- coding: utf-8 -*-
import logging
from urllib.parse import urljoin

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

    # Opcional: baixar e armazenar a imagem no Odoo
    poster_image = fields.Image(string="Cartaz (imagem)", max_width=1024, max_height=1024)

    last_sync = fields.Datetime(string="Última sincronização", readonly=True)

    _sql_constraints = [
        ("cineart_url_unique", "unique(cineart_url)", "Já existe um filme com este link do Cineart.")
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
        self.ensure_one()
        return self.env["guiabh.cineart.movie"].action_sync_all()

    @api.model
    def action_sync_all(self):
        Movie = self.sudo()
        results = Movie._run_sync(raise_on_error=True)
        message_lines = []
        for entry in results:
            if entry["valid"]:
                message_lines.append(
                    _(
                        "%(cat)s: %(count)s itens (%(created)s novos, %(updated)s atualizados, %(inactive)s inativados)"
                    )
                    % entry
                )
            else:
                message_lines.append(_("%(cat)s: sem mudanças (falha ou poucos itens)") % entry)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sincronização concluída"),
                "message": "\n".join(message_lines) if message_lines else _("Sincronização executada."),
                "type": "success",
                "sticky": False,
            },
        }

    # =========================
    # SINCRONIZAÇÃO
    # =========================

    @api.model
    def cron_sync_all(self):
        """Cron: sincroniza as 3 categorias."""
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

        _logger.info("Cineart sync: category=%s url=%s", category, url)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome Safari"
            )
        }
        try:
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
        except Exception as err:
            _logger.exception("Cineart sync HTTP error (%s): %s", category, err)
            if raise_on_error:
                raise UserError(_("Falha ao acessar %(url)s: %(msg)s") % {"url": url, "msg": err})
            return {"valid": False, "count": 0, "created": 0, "updated": 0, "inactivated": 0}

        try:
            doc = html.fromstring(response.content)
            items = self._parse_movies(doc, base_url=self.BASE_URL)
        except Exception as err:
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
            cineart_url = (item.get("cineart_url") or "").strip()
            cineart_url = self._normalize_cineart_url(cineart_url)
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
            except Exception as err:
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

    # -------- PARSER --------
    @api.model
    def _parse_movies(self, doc, base_url):
        """
        Parser robusto por heurística:
        - tenta achar cards clicáveis com imagem + título
        Ajuste aqui se o Cineart alterar a marcação.
        """
        results = []

        # Heurística 1: links que envolvem poster
        # (muitos sites usam <a ...><img ...> + titulo por perto)
        cards = doc.xpath("//a[.//img]")

        def clean(t):
            return " ".join((t or "").split()).strip()

        for a in cards:
            img = a.xpath(".//img[1]")
            if not img:
                continue

            poster_url = img[0].get("src") or img[0].get("data-src") or ""
            poster_url = poster_url.strip()

            # ignora ícones/brand
            if "logo" in poster_url.lower():
                continue

            href = a.get("href") or ""
            href = href.strip()
            cineart_url = urljoin(base_url, href) if href else ""

            # título: tenta aria-label, title, ou algum texto abaixo do card
            title = clean(a.get("title") or a.get("aria-label") or "")
            if not title:
                # tenta pegar texto do card
                title = clean(" ".join(a.xpath(".//text()")))
                # evita textos gigantes
                if len(title) > 80:
                    title = title[:80].strip()

            # filtro: precisa ter cara de filme
            if not title or len(title) < 2:
                continue

            # tenta achar metadados próximos (gênero/classificação/data)
            container = a.getparent()
            text_near = ""
            if container is not None:
                text_near = clean(" ".join(container.xpath(".//text()")))

            # heurísticas de extração simples
            age = ""
            if "16" in text_near:
                age = "16"
            elif "14" in text_near:
                age = "14"
            elif "12" in text_near:
                age = "12"
            elif "10" in text_near:
                age = "10"
            elif "18" in text_near:
                age = "18"
            elif "L" in text_near:
                # pode ser "L"
                age = "L"

            # data (muitas vezes vem como 01/01/2026)
            release = ""
            for token in text_near.split():
                if "/" in token and len(token) >= 8:
                    # bem simples, evita pegar lixo
                    if token.count("/") == 2:
                        release = token.strip()
                        break

            # gênero: tenta achar palavras típicas (isso é só “nice to have”)
            genre = ""
            for g in ["Ação", "Animação", "Infantil", "Terror", "Suspense", "Drama", "Comédia", "Aventura", "Romance"]:
                if g.lower() in text_near.lower():
                    genre = g
                    break

            # valida: garante que não é link do menu / redes sociais
            if any(x in cineart_url.lower() for x in ["instagram", "facebook", "twitter", "whatsapp"]):
                continue
            if "cineart.com.br" not in cineart_url.lower() and cineart_url:
                # pode ser relativo; urljoin resolve. Se ficou fora do domínio, ignora.
                continue

            results.append(
                {
                    "name": title,
                    "genre": genre,
                    "age_rating": age,
                    "release_date": release,
                    "cineart_url": cineart_url,
                    "poster_url": urljoin(base_url, poster_url) if poster_url else "",
                }
            )

        # remove duplicados por (nome + poster)
        dedup = []
        seen = set()
        for r in results:
            k = ((r.get("name") or "").lower(), (r.get("poster_url") or "").lower())
            if k in seen:
                continue
            seen.add(k)
            dedup.append(r)

        return dedup

    # -------- BAIXAR IMAGEM (opcional) --------
    def _try_fetch_image(self, rec):
        if not rec.poster_url:
            return
        try:
            r = requests.get(rec.poster_url, timeout=30)
            r.raise_for_status()
            rec.poster_image = r.content
        except Exception as e:
            _logger.warning("Falha ao baixar poster %s: %s", rec.poster_url, e)

    # -------- Helpers --------
    def _normalize_cineart_url(self, url):
        url = (url or "").strip()
        if not url:
            return False
        url = url.replace("http://", "https://")
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("https://www."):
            url = "https://" + url[12:]
        if url.startswith("http://www."):
            url = "http://" + url[11:]
            url = url.replace("http://", "https://", 1)
        if url.startswith("www."):
            url = "https://" + url[4:]
        return url
