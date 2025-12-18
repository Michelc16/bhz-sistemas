{
    "name": "GUIA BH - Hide Blog Date/Author",
    "version": "1.0.0",
    "category": "Website",
    "summary": "Esconde data/autor/meta nas páginas de post do blog (website_blog).",
    "depends": ["website", "website_blog"],
    "assets": {
        "web.assets_frontend": [
            "guiabh_blog_hide_meta/static/src/scss/blog_hide_meta.scss",
        ],
    },
    "installable": True,
    "application": False,
}
