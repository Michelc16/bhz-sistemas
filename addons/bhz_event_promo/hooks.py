# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Pós-instalação/upgrade.

    - Garante que modelos customizados tenham tabela no DB (em installs antigos que abortaram).
    - Mantém idempotente (pode rodar várias vezes).
    """
    _logger.warning("[BHZ EVENT PROMO] post_init_hook: garantindo tabelas...")

    # Lista de modelos que historicamente ficam sem tabela quando a instalação aborta
    models_to_ensure = [
        "bhz.portalbh.carnaval.import.job",
        "bhz.portalbh.carnaval.import.wizard",
        "bhz.event.import.wizard",
    ]

    for model_name in models_to_ensure:
        try:
            model = env[model_name]
        except Exception as e:
            _logger.warning("[BHZ EVENT PROMO] model não encontrado (%s): %s", model_name, e)
            continue

        try:
            # _auto_init cria a tabela/colunas que estiverem faltando
            model._auto_init()
            _logger.warning("[BHZ EVENT PROMO] ok: tabela garantida para %s", model_name)
        except Exception as e:
            _logger.exception("[BHZ EVENT PROMO] falha ao garantir tabela %s: %s", model_name, e)
