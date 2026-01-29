import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = "website"

    bhz_featured_carousel_autoplay = fields.Boolean(
        string="Autoplay do carrossel de destaques",
        help="Se marcado, o carrossel de destaques roda automaticamente.",
    )
    bhz_featured_carousel_interval_ms = fields.Integer(
        string="Intervalo do carrossel (ms)",
        help="Tempo entre slides do carrossel de destaques.",
    )
    bhz_featured_carousel_refresh_ms = fields.Integer(
        string="Atualização do carrossel (ms)",
        help="Frequência de atualização automática do carrossel. 0 desabilita.",
    )

    @api.model_cr
    def init(self):
        """Create the featured carousel columns if they are missing.

        Some staging databases were deployed without running a module upgrade
        after these fields were introduced, which makes PostgreSQL raise
        UndefinedColumn errors during website requests. This hook ensures the
        three columns exist before the ORM tries to read them, avoiding 500s
        without requiring a manual DB migration step.
        """

        cr = self._cr
        cr.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'website'
            AND column_name IN (
                'bhz_featured_carousel_autoplay',
                'bhz_featured_carousel_interval_ms',
                'bhz_featured_carousel_refresh_ms'
            )
            """
        )
        existing = {row[0] for row in cr.fetchall()}

        definitions = [
            ("bhz_featured_carousel_autoplay", "boolean", "TRUE"),
            ("bhz_featured_carousel_interval_ms", "integer", "5000"),
            ("bhz_featured_carousel_refresh_ms", "integer", "60000"),
        ]

        for name, pg_type, default in definitions:
            if name in existing:
                continue
            try:
                _logger.warning("Adding missing column website.%s on the fly", name)
                cr.execute(f'ALTER TABLE website ADD COLUMN "{name}" {pg_type} DEFAULT {default}')
            except Exception:  # pragma: no cover - safeguard for DB state
                _logger.exception("Failed to create website.%s column", name)

        # Let the normal ORM initialization continue
        return super().init()
