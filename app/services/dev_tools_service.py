"""
dev_tools_service.py

Ferramentas de desenvolvimento/teste.
Limpeza segura de dados de teste no Snowflake, preservando dados seed/base.

Critério de identificação:
  - Dados SEED (base): SUPPLIER_ID formato 's-NNN', USER_ID formato 'u-NNN',
    WINDOW_ID formato 'w-NNN'.
  - Dados de TESTE (criados pelo app): IDs em formato UUID (36 chars).

Segurança:
  - Só executa quando APP_ENV != 'production'.
  - Respeita ordem de dependências (filhas → pais).
  - Retorna contagem de registros removidos por tabela.
  - Não mascara erros.
"""

import logging

from services.snowflake_service import get_snowflake_session
from utils.constants import APP_ENV

logger = logging.getLogger(__name__)

DATABASE = "KBI_DATA_JOURNEY_DEV_DB"

# Tabelas na ordem de limpeza (filhas primeiro, pais por último)
_CLEANUP_STEPS = [
    {
        "label": "CONTROL.VALIDATION_ERRORS",
        "sql": (
            f"DELETE FROM {DATABASE}.CONTROL.VALIDATION_ERRORS "
            f"WHERE UPLOAD_ID IN ("
            f"  SELECT UPLOAD_ID FROM {DATABASE}.CONTROL.UPLOAD_BATCHES "
            f"  WHERE SUPPLIER_ID NOT LIKE 's-%'"
            f")"
        ),
    },
    {
        "label": "TRUSTED.FORECAST_VALIDATED",
        "sql": (
            f"DELETE FROM {DATABASE}.TRUSTED.FORECAST_VALIDATED "
            f"WHERE UPLOAD_ID IN ("
            f"  SELECT UPLOAD_ID FROM {DATABASE}.CONTROL.UPLOAD_BATCHES "
            f"  WHERE SUPPLIER_ID NOT LIKE 's-%'"
            f")"
        ),
    },
    {
        "label": "STAGING.FORECAST_NORMALIZED",
        "sql": (
            f"DELETE FROM {DATABASE}.STAGING.FORECAST_NORMALIZED "
            f"WHERE UPLOAD_ID IN ("
            f"  SELECT UPLOAD_ID FROM {DATABASE}.CONTROL.UPLOAD_BATCHES "
            f"  WHERE SUPPLIER_ID NOT LIKE 's-%'"
            f")"
        ),
    },
    {
        "label": "RAW.UPLOADED_FILE_ROWS",
        "sql": (
            f"DELETE FROM {DATABASE}.RAW.UPLOADED_FILE_ROWS "
            f"WHERE UPLOAD_ID IN ("
            f"  SELECT UPLOAD_ID FROM {DATABASE}.CONTROL.UPLOAD_BATCHES "
            f"  WHERE SUPPLIER_ID NOT LIKE 's-%'"
            f")"
        ),
    },
    {
        "label": "CONTROL.UPLOAD_BATCHES",
        "sql": (
            f"DELETE FROM {DATABASE}.CONTROL.UPLOAD_BATCHES "
            f"WHERE SUPPLIER_ID NOT LIKE 's-%'"
        ),
    },
    {
        "label": "CONTROL.USERS",
        "sql": (
            f"DELETE FROM {DATABASE}.CONTROL.USERS "
            f"WHERE USER_ID NOT LIKE 'u-%'"
        ),
    },
    {
        "label": "CONTROL.SUPPLIERS",
        "sql": (
            f"DELETE FROM {DATABASE}.CONTROL.SUPPLIERS "
            f"WHERE SUPPLIER_ID NOT LIKE 's-%'"
        ),
    },
]


def clear_dev_data() -> dict:
    """
    Remove dados de teste do Snowflake, preservando dados seed/base.

    Retorna:
        {"success": True, "deleted": {"tabela": N, ...}, "errors": []}
        ou
        {"success": False, "deleted": {}, "errors": ["mensagem"]}
    """
    result = {"success": False, "deleted": {}, "errors": []}

    # Guard: bloquear em produção
    if APP_ENV in ("production", "prod"):
        msg = (
            f"[dev_tools] BLOQUEADO: clear_dev_data() não pode executar "
            f"com APP_ENV='{APP_ENV}'. Defina APP_ENV=dev para usar."
        )
        logger.error(msg)
        result["errors"].append(msg)
        return result

    session = get_snowflake_session()
    if session is None:
        msg = (
            "[dev_tools] Sessão Snowflake indisponível. "
            "Não foi possível limpar dados de teste."
        )
        logger.error(msg)
        result["errors"].append(msg)
        return result

    logger.info(
        "[dev_tools] Iniciando limpeza de dados de teste (APP_ENV=%s)...",
        APP_ENV,
    )

    for step in _CLEANUP_STEPS:
        label = step["label"]
        sql = step["sql"]
        try:
            rows = session.sql(sql).collect()
            # Snowpark DELETE retorna Row com 'number of rows deleted'
            count = rows[0][0] if rows else 0
            result["deleted"][label] = count
            logger.info("[dev_tools]   %s: %d registros removidos.", label, count)
        except Exception as exc:
            msg = f"[dev_tools] Erro ao limpar {label}: {type(exc).__name__}: {exc}"
            logger.error(msg)
            result["errors"].append(msg)
            result["deleted"][label] = f"ERRO: {exc}"

    result["success"] = len(result["errors"]) == 0
    logger.info(
        "[dev_tools] Limpeza %s. Resumo: %s",
        "concluída" if result["success"] else "com erros",
        result["deleted"],
    )
    return result
