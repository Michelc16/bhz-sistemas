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

    CINEART_ROUTES = {
        "now": "https://www.cineart.com.br/em-cartaz",
        "soon": "https://www.cineart.com.br/em-breve",
        "premiere": "https://www.cineart.com.br/estreias",
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
        message_lines = []
        Movie = self.sudo()
        categories = [
            ("now", _("Em cartaz")),
            ("soon", _("Em breve")),
            ("premiere", _("Estreias da semana")),
        ]
        for code, label in categories:
            route = Movie.CINEART_ROUTES.get(code)
            try:
                result = Movie._sync_category(route, code, raise_on_error=True)
            except UserError:
                raise
            except Exception as err:
                _logger.exception("Erro inesperado ao sincronizar categoria %s via botão", code)
                raise UserError(_("Falha ao sincronizar %(cat)s: %(msg)s") % {"cat": label, "msg": err})

            if not result or not result.get("valid"):
                message_lines.append(_("%s: sem mudanças (falha ou nada novo)") % label)
            else:
                message_lines.append(_("%(cat)s: %(count)s itens") % {"cat": label, "count": result.get("count", 0)})

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
        for code, url in self.CINEART_ROUTES.items():
            try:
                self._sync_category(url, code)
            except Exception:
                _logger.exception("Erro ao sincronizar categoria %s via cron", code)

    @api.model
    def sync_category(self, category):
        """Compatibilidade antiga."""
        route = self.CINEART_ROUTES.get(category)
        return self._sync_category(route, category, raise_on_error=True)

    @api.model
    def _sync_category(self, url, category, raise_on_error=False):
        if not url:
            msg = _("Categoria inválida: %s") % (category,)
            _logger.error("Cineart sync aborted: %s", msg)
            if raise_on_error:
                raise UserError(msg)
            return {"valid": False, "count": 0}

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
            return {"valid": False, "count": 0}

        try:
            doc = html.fromstring(response.content)
            items = self._parse_movies(doc, base_url="https://www.cineart.com.br/")
        except Exception as err:
            _logger.exception("Cineart parse error (%s): %s", category, err)
            if raise_on_error:
                raise UserError(_("Falha ao interpretar os dados de %(cat)s: %(msg)s") % {"cat": category, "msg": err})
            return {"valid": False, "count": 0}

        if not items or len(items) < self.MIN_VALID_ITEMS:
            _logger.warning(
                "Cineart sync aborted (%s): encontrou %s itens (< %s)",
                category,
                len(items) if items else 0,
                self.MIN_VALID_ITEMS,
            )
            return {"valid": False, "count": len(items) if items else 0}

        existing = self.search([("category", "=", category)])
        existing_by_key = {self._build_sync_key(rec.name, rec.cineart_url, rec.category): rec for rec in existing}
        seen_keys = set()
        now = fields.Datetime.now()

        for item in items:
            key = self._build_sync_key(item.get("name"), item.get("cineart_url"), category)
            if not key:
                continue
            seen_keys.add(key)
            vals = {
                "name": item.get("name"),
                "category": category,
                "genre": item.get("genre"),
                "age_rating": item.get("age_rating"),
                "release_date": item.get("release_date"),
                "cineart_url": item.get("cineart_url"),
                "poster_url": item.get("poster_url"),
                "active": True,
                "last_sync": now,
            }
            rec = existing_by_key.get(key)
            if rec:
                rec.write(vals)
            else:
                rec = self.create(vals)
                existing_by_key[key] = rec
            self._try_fetch_image(rec)

        for rec in existing:
            rec_key = self._build_sync_key(rec.name, rec.cineart_url, rec.category)
            if rec_key and rec_key not in seen_keys:
                rec.active = False

        _logger.info("Cineart sync DONE: category=%s items=%s", category, len(items))
        return {"valid": True, "count": len(items)}

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
    def _build_sync_key(self, name, url, category):
        url = (url or "").strip().lower()
        if url:
            return url
        name = (name or "").strip().lower()
        if not name:
            return False
        return "%s|%s" % ((category or "").strip().lower(), name)

    def _try_fetch_image(self, rec):
        if not rec.poster_url:
            return
        try:
            r = requests.get(rec.poster_url, timeout=30)
            r.raise_for_status()
            rec.poster_image = r.content
        except Exception as e:
            _logger.warning("Falha ao baixar poster %s: %s", rec.poster_url, e)
