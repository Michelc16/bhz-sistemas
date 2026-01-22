from odoo import http
from odoo.http import request
from odoo.tools import html_escape


def _sitemap_records(env, model_name, url_prefix):
    Model = env[model_name].sudo()
    domain = [("website_published", "=", True), ("slug", "!=", False)]
    for rec in Model.search(domain):
        yield {"loc": f"{url_prefix}{rec.slug}"}


class GuiaBHWebsite(http.Controller):
    @http.route(
        "/<string:slug>",
        type="http",
        auth="public",
        website=True,
        sitemap=lambda env, url, qs: list(_sitemap_records(env, "guiabh.category", "/")),
    )
    def render_category_page(self, slug, **kwargs):
        Category = request.env["guiabh.category"].sudo()
        category = Category.search(
            [("slug", "=", slug), ("website_published", "=", True)], limit=1
        )
        if not category:
            return request.not_found()

        def _fetch(model_name, date_field=None, limit=9):
            Model = request.env[model_name].sudo()
            domain = [
                    ("category_id", "=", category.id),
                    ("website_published", "=", True),
                ]
            order = "featured desc"
            if date_field:
                order += f", {date_field} desc"
            else:
                order += ", name asc"
            return Model.search(domain, limit=limit, order=order)

        events = _fetch("guiabh.event", date_field="start_datetime", limit=6)
        places = _fetch("guiabh.place", date_field=None, limit=6)
        movies = _fetch("guiabh.movie", date_field="release_date", limit=6)
        matches = _fetch("guiabh.match", date_field="match_datetime", limit=6)
        news = _fetch("guiabh.news", date_field="publish_date", limit=6)

        values = {
            "category": category,
            "events": events,
            "places": places,
            "movies": movies,
            "matches": matches,
            "news": news,
            "seo_title": category.website_meta_title or category.name,
            "seo_description": category.website_meta_description
            or (category.description and html_escape(category.description[:160]))
            or f"Explore {category.name} em Belo Horizonte.",
            "canonical_url": f"/{category.slug}",
            "breadcrumb": [
                {"label": "Home", "url": "/"},
                {"label": category.name, "url": f"/{category.slug}"},
            ],
            "og_image": category.cover_image
            and f"/web/image/guiabh.category/{category.id}/cover_image"
            or "/web/static/img/logo.png",
        }
        return request.render("bhz_guiabh_website.guiabh_category_page", values)

    # Detail pages
    def _render_detail(self, model_name, slug, schema_type, url_prefix):
        Model = request.env[model_name].sudo()
        record = Model.search(
            [("slug", "=", slug), ("website_published", "=", True)], limit=1
        )
        if not record:
            return request.not_found()

        category = getattr(record, "category_id", False)
        description = (
            getattr(record, "website_meta_description", None)
            or getattr(record, "description", None)
            or ""
        )
        og_image = (
            record.cover_image
            and f"/web/image/{model_name}/{record.id}/cover_image"
            or "/web/static/img/logo.png"
        )

        breadcrumb = [{"label": "Home", "url": "/"}]
        if category:
            breadcrumb.append({"label": category.name, "url": f"/{category.slug or ''}"})
        breadcrumb.append({"label": record.name, "url": f"{url_prefix}{record.slug}"})

        values = {
            "record": record,
            "schema_type": schema_type,
            "description": description,
            "og_image": og_image,
            "canonical_url": f"{url_prefix}{record.slug}",
            "breadcrumb": breadcrumb,
            "page_title": getattr(record, "website_meta_title", None) or record.name,
            "page_description": html_escape(description[:160]) if description else "",
        }
        return request.render("bhz_guiabh_website.guiabh_content_detail", values)

    @http.route(
        "/g/event/<string:slug>",
        type="http",
        auth="public",
        website=True,
        sitemap=lambda env, url, qs: list(_sitemap_records(env, "guiabh.event", "/g/event/")),
    )
    def render_event(self, slug, **kwargs):
        return self._render_detail("guiabh.event", slug, "Event", "/g/event/")

    @http.route(
        "/g/place/<string:slug>",
        type="http",
        auth="public",
        website=True,
        sitemap=lambda env, url, qs: list(_sitemap_records(env, "guiabh.place", "/g/place/")),
    )
    def render_place(self, slug, **kwargs):
        return self._render_detail("guiabh.place", slug, "Place", "/g/place/")

    @http.route(
        "/g/movie/<string:slug>",
        type="http",
        auth="public",
        website=True,
        sitemap=lambda env, url, qs: list(_sitemap_records(env, "guiabh.movie", "/g/movie/")),
    )
    def render_movie(self, slug, **kwargs):
        return self._render_detail("guiabh.movie", slug, "Movie", "/g/movie/")

    @http.route(
        "/g/match/<string:slug>",
        type="http",
        auth="public",
        website=True,
        sitemap=lambda env, url, qs: list(_sitemap_records(env, "guiabh.match", "/g/match/")),
    )
    def render_match(self, slug, **kwargs):
        return self._render_detail("guiabh.match", slug, "SportsEvent", "/g/match/")

    @http.route(
        "/g/news/<string:slug>",
        type="http",
        auth="public",
        website=True,
        sitemap=lambda env, url, qs: list(_sitemap_records(env, "guiabh.news", "/g/news/")),
    )
    def render_news(self, slug, **kwargs):
        return self._render_detail("guiabh.news", slug, "Article", "/g/news/")
