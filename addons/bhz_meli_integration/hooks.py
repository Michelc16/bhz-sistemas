import logging

_logger = logging.getLogger(__name__)


def _ensure_cron(env, xmlid, name, model_name, method_code, interval_number, interval_type):
    """
    Garante que o cron exista e esteja visível para todas as empresas (company_id=False).
    Também evita dependência de XML em caso de inconsistência de xmlid/upgrade.
    """
    IrCron = env["ir.cron"].sudo()
    IrModel = env["ir.model"].sudo()

    model = IrModel.search([("model", "=", model_name)], limit=1)
    if not model:
        _logger.warning("[ML] Model %s não encontrado. Cron %s não criado.", model_name, name)
        return

    # tenta achar por xmlid
    cron = None
    try:
        cron = env.ref(xmlid, raise_if_not_found=False)
    except Exception:
        cron = None

    vals = {
        "name": name,
        "model_id": model.id,
        "state": "code",
        "code": method_code,
        "interval_number": interval_number,
        "interval_type": interval_type,
        "active": True,
        "user_id": env.ref("base.user_root").id,
        "company_id": False,  # <- ESSENCIAL (visível em multi-company)
    }

    if cron and cron.exists():
        cron.sudo().write(vals)
        _logger.warning("[ML] Cron atualizado: %s", name)
    else:
        cron = IrCron.create(vals)
        _logger.warning("[ML] Cron criado: %s (id=%s)", name, cron.id)

        # registra xmlid (para ficar rastreável e manter upgrades)
        module, rec_name = xmlid.split(".", 1)
        env["ir.model.data"].sudo().create({
            "name": rec_name,
            "model": "ir.cron",
            "module": module,
            "res_id": cron.id,
            "noupdate": False,
        })


def post_init_hook(env):
    """
    Roda depois da instalação/upgrade do módulo.
    """
    _logger.warning("[ML] post_init_hook: garantindo crons do Mercado Livre...")

    _ensure_cron(
        env=env,
        xmlid="bhz_meli_integration.bhz_meli_cron_fetch_orders",
        name="BHZ ML: Buscar pedidos",
        model_name="meli.order",
        method_code="model.cron_fetch_orders()",
        interval_number=10,
        interval_type="minutes",
    )

    _ensure_cron(
        env=env,
        xmlid="bhz_meli_integration.bhz_meli_cron_fetch_items",
        name="BHZ ML: Buscar anúncios",
        model_name="meli.product",
        method_code="model.cron_fetch_items()",
        interval_number=30,
        interval_type="minutes",
    )
