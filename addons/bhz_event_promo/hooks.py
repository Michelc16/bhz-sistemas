# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def _table_exists(cr, table_name: str) -> bool:
    cr.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s)",
        (table_name,),
    )
    return bool(cr.fetchone()[0])

def _create_portalbh_carnaval_tables_if_missing(cr):
    """
    Odoo.sh sometimes upgrades an existing DB where these models are already registered
    (ir.model / ir.model.fields), but the underlying SQL tables may have been dropped
    or never created (e.g. aborted upgrade). That causes:
        ERROR Model bhz.portalbh.carnaval.import.(job|wizard) has no table.
    This hook makes the upgrade idempotent by creating the missing tables.
    """
    # Persistent Job model (models.Model)
    job_table = "bhz_portalbh_carnaval_import_job"
    if not _table_exists(cr, job_table):
        _logger.warning("[bhz_event_promo] Creating missing table: %s", job_table)
        cr.execute(f"""
            CREATE TABLE "{job_table}" (
                id SERIAL PRIMARY KEY,
                create_uid INTEGER,
                create_date TIMESTAMP,
                write_uid INTEGER,
                write_date TIMESTAMP,

                name VARCHAR NOT NULL,
                state VARCHAR NOT NULL,
                source_url VARCHAR NOT NULL,

                max_pages INTEGER,
                current_page INTEGER,
                update_existing BOOLEAN,
                default_duration_hours DOUBLE PRECISION,

                created_count INTEGER,
                updated_count INTEGER,
                skipped_count INTEGER,
                error_count INTEGER,

                last_run TIMESTAMP,
                log TEXT,

                pages_per_cron INTEGER,
                request_timeout_connect INTEGER,
                request_timeout_read INTEGER,
                image_max_bytes INTEGER,

                company_id INTEGER,
                website_id INTEGER
            )
        """)

    # Wizard (models.TransientModel) - still needs a backing table
    wiz_table = "bhz_portalbh_carnaval_import_wizard"
    if not _table_exists(cr, wiz_table):
        _logger.warning("[bhz_event_promo] Creating missing table: %s", wiz_table)
        cr.execute(f"""
            CREATE TABLE "{wiz_table}" (
                id SERIAL PRIMARY KEY,
                create_uid INTEGER,
                create_date TIMESTAMP,
                write_uid INTEGER,
                write_date TIMESTAMP,

                source_url VARCHAR NOT NULL,
                max_pages INTEGER,
                update_existing BOOLEAN,
                default_duration_hours DOUBLE PRECISION,

                company_id INTEGER NOT NULL,
                website_id INTEGER
            )
        """)

def post_init_hook(env):
    """Post-init hook called by Odoo with an *env* (since v19).

    The build was failing with:
        - Model bhz.portalbh.carnaval.import.wizard has no table.
        - Model bhz.portalbh.carnaval.import.job has no table.

    This hook is intentionally defensive and idempotent.
    """
    cr = env.cr
    try:
        _create_portalbh_carnaval_tables_if_missing(cr)
    except Exception:
        _logger.exception("[bhz_event_promo] post_init_hook failed while creating missing tables")
