"""
submission_window_service.py

Service dedicado para gerenciamento de Janelas de Envio (CONTROL.SUBMISSION_WINDOWS).
Responsavel por: consultar janela aberta, listar janelas, criar, fechar e abrir janelas.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from utils.logger import get_logger
from utils.constants import DEFAULT_REPORT_TYPE, APP_ENV

_logger = get_logger(__name__)

_DATABASE = "KBI_DATA_JOURNEY_DEV_DB"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _calculate_progress_pct(start_date, end_date) -> int:
    """Calcula percentual de progresso da janela com base na data atual."""
    today = date.today()
    try:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
    except (ValueError, TypeError):
        return 0

    if today < start_date:
        return 0
    if today > end_date:
        return 100

    total_days = (end_date - start_date).days
    if total_days <= 0:
        return 100
    elapsed = (today - start_date).days
    return min(100, max(0, int((elapsed / total_days) * 100)))


def _format_date_br(d) -> str:
    """Formata data para DD/MM/YYYY."""
    try:
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        if isinstance(d, datetime):
            d = d.date()
        return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError, AttributeError):
        return str(d) if d else ""


def _row_to_dict(row: dict) -> dict:
    """Converte row do Snowflake para dict padronizado."""
    start_d = row.get("START_DATE", "")
    end_d = row.get("END_DATE", "")
    ref_period = str(row.get("REFERENCE_PERIOD", ""))
    report_type = str(row.get("REPORT_TYPE", DEFAULT_REPORT_TYPE))
    is_open = bool(row.get("IS_OPEN", False))

    # Label legivel
    try:
        year, month = ref_period.split("-")
        months = [
            "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]
        label = f"{months[int(month) - 1]}/{year}"
    except (ValueError, IndexError):
        label = ref_period

    start_br = _format_date_br(start_d)
    end_br = _format_date_br(end_d)
    progress = _calculate_progress_pct(start_d, end_d) if is_open else 0

    return {
        "window_id": str(row.get("WINDOW_ID", "")),
        "report_type": report_type,
        "reference_period": ref_period,
        "period": ref_period,
        "start_date": start_br,
        "end_date": end_br,
        "closes_at": end_br,
        "label": label,
        "is_open": is_open,
        "open": is_open,
        "progress_pct": progress,
        "created_at": str(row.get("CREATED_AT", "")),
        "created_by": str(row.get("CREATED_BY", "")),
    }


# ---------------------------------------------------------------------------
# Mock fallback (dev/demo only)
# ---------------------------------------------------------------------------

_MOCK_WINDOW = {
    "window_id": "__MOCK__",
    "report_type": DEFAULT_REPORT_TYPE,
    "reference_period": "2026-06",
    "period": "2026-06",
    "start_date": "01/06/2026",
    "end_date": "30/06/2026",
    "closes_at": "30/06/2026",
    "label": "Junho/2026",
    "is_open": True,
    "open": True,
    "progress_pct": 30,
    "created_at": "",
    "created_by": "",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _auto_close_expired_windows(session, safe_rt: str) -> None:
    """Fecha automaticamente janelas OPEN cujo END_DATE < CURRENT_DATE."""
    try:
        session.sql(f"""
            UPDATE {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            SET IS_OPEN = FALSE
            WHERE IS_OPEN = TRUE
              AND REPORT_TYPE = '{safe_rt}'
              AND END_DATE < CURRENT_DATE
        """).collect()
        _logger.info("Janelas expiradas fechadas automaticamente para report_type='%s'.", safe_rt)
    except Exception as exc:
        _logger.exception("Falha ao fechar janelas expiradas automaticamente: %s", exc)

def get_current_open_window(report_type: str = DEFAULT_REPORT_TYPE) -> Optional[dict]:
    """
    Retorna a janela aberta atual para o report_type informado.

    Regras:
    - IS_OPEN = TRUE
    - CURRENT_DATE entre START_DATE e END_DATE (inclusive)
    - REPORT_TYPE = report_type

    Se houver mais de uma, seleciona a mais recente por CREATED_AT e loga warning.
    Se a tabela estiver vazia e APP_ENV in (dev, test, local), retorna mock fallback.
    Retorna None se nenhuma janela aberta encontrada.
    """
    try:
        from services.snowflake_service import get_snowflake_session
        session = get_snowflake_session()
        if session is None:
            if APP_ENV in ("dev", "test", "local"):
                _logger.warning("Sem sessao Snowflake; usando mock window (APP_ENV=%s)", APP_ENV)
                return dict(_MOCK_WINDOW)
            return None

        safe_rt = report_type.replace("'", "''")
        query = f"""
            SELECT *
            FROM {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            WHERE IS_OPEN = TRUE
              AND REPORT_TYPE = '{safe_rt}'
              AND CURRENT_DATE BETWEEN START_DATE AND END_DATE
            ORDER BY CREATED_AT DESC
        """
        df = session.sql(query).to_pandas()

        if df is not None and not df.empty:
            if len(df) > 1:
                _logger.warning(
                    "Mais de uma janela aberta encontrada para report_type='%s'. "
                    "Usando a mais recente (WINDOW_ID=%s).",
                    report_type, df.iloc[0]["WINDOW_ID"],
                )
            row = df.iloc[0].to_dict()
            return _row_to_dict(row)

        # Tabela existe mas nenhuma janela aberta valida
        # Verificar se ha alguma janela OPEN sem filtro de data (pode estar fora do range)
        df_any = session.sql(f"""
            SELECT COUNT(*) AS CNT
            FROM {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            WHERE IS_OPEN = TRUE AND REPORT_TYPE = '{safe_rt}'
        """).to_pandas()

        if df_any is not None and not df_any.empty and int(df_any.iloc[0]["CNT"]) > 0:
            # Ha janela OPEN mas fora do periodo de datas — fechar automaticamente (expirada)
            _logger.info(
                "Janela OPEN encontrada para '%s' mas fora do intervalo de datas atual. "
                "Fechando automaticamente (expiracao).",
                report_type,
            )
            _auto_close_expired_windows(session, safe_rt)
            return None

        # Nenhuma janela criada/aberta — fallback mock se dev
        total = session.sql(f"""
            SELECT COUNT(*) AS CNT FROM {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
        """).to_pandas()
        is_empty = total is not None and not total.empty and int(total.iloc[0]["CNT"]) == 0

        if is_empty and APP_ENV in ("dev", "test", "local"):
            _logger.warning(
                "Tabela SUBMISSION_WINDOWS vazia; usando mock window (APP_ENV=%s)", APP_ENV,
            )
            return dict(_MOCK_WINDOW)

        return None

    except Exception as exc:
        _logger.exception("Erro ao buscar janela aberta: %s", exc)
        if APP_ENV in ("dev", "test", "local"):
            _logger.warning("Fallback mock window apos excecao (APP_ENV=%s)", APP_ENV)
            return dict(_MOCK_WINDOW)
        return None


def list_submission_windows(report_type: Optional[str] = None) -> list[dict]:
    """
    Lista todas as janelas de envio cadastradas, ordenadas da mais recente para a mais antiga.
    Se report_type informado, filtra por ele.
    """
    try:
        from services.snowflake_service import get_snowflake_session
        session = get_snowflake_session()
        if session is None:
            return []

        where = ""
        if report_type:
            safe_rt = report_type.replace("'", "''")
            where = f"WHERE REPORT_TYPE = '{safe_rt}'"

        query = f"""
            SELECT *
            FROM {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            {where}
            ORDER BY CREATED_AT DESC
        """
        df = session.sql(query).to_pandas()
        if df is None or df.empty:
            return []

        return [_row_to_dict(row.to_dict()) for _, row in df.iterrows()]

    except Exception as exc:
        _logger.exception("Erro ao listar janelas: %s", exc)
        return []


def create_submission_window(
    report_type: str,
    reference_period: str,
    start_date: date,
    end_date: date,
    created_by: str,
) -> dict | None:
    """
    Cria uma nova janela de envio.

    Validacoes:
    - reference_period deve estar no formato YYYY-MM
    - start_date <= end_date
    - Nao pode haver outra janela OPEN com datas sobrepostas para o mesmo report_type

    Retorna dict da janela criada, ou None em caso de erro.
    """
    # Validar formato
    import re
    if not re.match(r"^\d{4}-\d{2}$", reference_period):
        _logger.error("Formato de reference_period invalido: %s", reference_period)
        return None

    if start_date > end_date:
        _logger.error("start_date (%s) > end_date (%s)", start_date, end_date)
        return None

    if end_date < date.today():
        _logger.error("end_date (%s) anterior a data atual (%s)", end_date, date.today())
        return None

    try:
        from services.snowflake_service import get_snowflake_session
        session = get_snowflake_session()
        if session is None:
            _logger.error("Sem sessao Snowflake para criar janela.")
            return None

        safe_rt = report_type.replace("'", "''")
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Verificar sobreposicao com janela aberta do mesmo report_type
        overlap_query = f"""
            SELECT COUNT(*) AS CNT
            FROM {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            WHERE IS_OPEN = TRUE
              AND REPORT_TYPE = '{safe_rt}'
              AND (START_DATE <= '{end_str}' AND END_DATE >= '{start_str}')
        """
        df_overlap = session.sql(overlap_query).to_pandas()
        if df_overlap is not None and not df_overlap.empty and int(df_overlap.iloc[0]["CNT"]) > 0:
            _logger.warning(
                "Janela sobreposta encontrada para report_type='%s' no intervalo %s a %s.",
                report_type, start_str, end_str,
            )
            return None

        window_id = str(uuid.uuid4())
        safe_by = created_by.replace("'", "''")

        insert_sql = f"""
            INSERT INTO {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
                (WINDOW_ID, REPORT_TYPE, REFERENCE_PERIOD, START_DATE, END_DATE, IS_OPEN, CREATED_BY)
            VALUES
                ('{window_id}', '{safe_rt}', '{reference_period}', '{start_str}', '{end_str}', TRUE, '{safe_by}')
        """
        session.sql(insert_sql).collect()
        _logger.info(
            "Janela criada: window_id=%s, report_type=%s, period=%s, %s a %s",
            window_id, report_type, reference_period, start_str, end_str,
        )

        return {
            "window_id": window_id,
            "report_type": report_type,
            "reference_period": reference_period,
            "period": reference_period,
            "start_date": _format_date_br(start_date),
            "end_date": _format_date_br(end_date),
            "closes_at": _format_date_br(end_date),
            "label": reference_period,
            "is_open": True,
            "open": True,
            "progress_pct": _calculate_progress_pct(start_date, end_date),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_by": created_by,
        }

    except Exception as exc:
        _logger.exception("Erro ao criar janela: %s", exc)
        return None


def close_submission_window(window_id: str, updated_by: str) -> bool:
    """
    Fecha uma janela de envio (IS_OPEN = FALSE).
    Nao apaga o registro.
    """
    try:
        from services.snowflake_service import get_snowflake_session
        session = get_snowflake_session()
        if session is None:
            _logger.error("Sem sessao Snowflake para fechar janela.")
            return False

        safe_id = window_id.replace("'", "''")
        update_sql = f"""
            UPDATE {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            SET IS_OPEN = FALSE
            WHERE WINDOW_ID = '{safe_id}'
        """
        session.sql(update_sql).collect()
        _logger.info("Janela fechada: window_id=%s, by=%s", window_id, updated_by)
        return True

    except Exception as exc:
        _logger.exception("Erro ao fechar janela: %s", exc)
        return False


def open_submission_window(window_id: str, updated_by: str) -> bool:
    """
    Abre uma janela de envio (IS_OPEN = TRUE).
    Verifica se nao ha conflito com outra janela aberta do mesmo report_type com datas sobrepostas.
    """
    try:
        from services.snowflake_service import get_snowflake_session
        session = get_snowflake_session()
        if session is None:
            _logger.error("Sem sessao Snowflake para abrir janela.")
            return False

        safe_id = window_id.replace("'", "''")

        # Buscar dados da janela a ser aberta
        df_target = session.sql(f"""
            SELECT REPORT_TYPE, START_DATE, END_DATE
            FROM {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            WHERE WINDOW_ID = '{safe_id}'
        """).to_pandas()

        if df_target is None or df_target.empty:
            _logger.error("Janela nao encontrada: window_id=%s", window_id)
            return False

        row = df_target.iloc[0]
        rt = str(row["REPORT_TYPE"]).replace("'", "''")
        start_str = str(row["START_DATE"])[:10]
        end_str = str(row["END_DATE"])[:10]

        # Verificar conflito
        overlap_query = f"""
            SELECT COUNT(*) AS CNT
            FROM {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            WHERE IS_OPEN = TRUE
              AND REPORT_TYPE = '{rt}'
              AND WINDOW_ID != '{safe_id}'
              AND (START_DATE <= '{end_str}' AND END_DATE >= '{start_str}')
        """
        df_overlap = session.sql(overlap_query).to_pandas()
        if df_overlap is not None and not df_overlap.empty and int(df_overlap.iloc[0]["CNT"]) > 0:
            _logger.warning(
                "Conflito: outra janela aberta sobreposta para report_type='%s'. "
                "Nao e possivel abrir window_id=%s.", rt, window_id,
            )
            return False

        update_sql = f"""
            UPDATE {_DATABASE}.CONTROL.SUBMISSION_WINDOWS
            SET IS_OPEN = TRUE
            WHERE WINDOW_ID = '{safe_id}'
        """
        session.sql(update_sql).collect()
        _logger.info("Janela aberta: window_id=%s, by=%s", window_id, updated_by)
        return True

    except Exception as exc:
        _logger.exception("Erro ao abrir janela: %s", exc)
        return False
