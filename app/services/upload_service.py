"""
upload_service.py

Serviço de recebimento e processamento de arquivos enviados pelo fornecedor.
Responsável por ler o arquivo .xlsx ou .csv, parsear o conteúdo em DataFrame
e preparar os dados para a etapa de validação.
Não realiza upload real ao Snowflake nesta fase.

Dados mockados centralizados em services/mock_data_service.py.
"""

from dataclasses import dataclass, field
from typing import Optional

from services.mock_data_service import (
    get_mock_uploads,
    get_mock_upload_by_id,
    get_current_open_window,
)
from utils.constants import DEFAULT_REPORT_TYPE


# ---------------------------------------------------------------------------
# Tipos de dados
# ---------------------------------------------------------------------------

@dataclass
class UploadRecord:
    """Representa um registro de envio no histórico do fornecedor."""
    upload_id:    str
    file_name:    str
    period:       str    # AAAA-MM
    version:      int
    status:       str    # valid | invalid | replaced | canceled
    sent_at:      str    # DD/MM/AAAA HH:MM
    valid_rows:   int
    invalid_rows: int
    supplier_id:  str    # vem do session_state, nunca da planilha
    is_active:    bool = False   # True apenas para o upload VALID vigente da chave
    report_type:  str = DEFAULT_REPORT_TYPE


@dataclass
class ValidationCheck:
    """Representa um item do resumo de validação."""
    check:       str
    result:      str   # "OK" | "ERRO"
    observation: str


@dataclass
class ProcessingStep:
    """Representa uma etapa da timeline de processamento."""
    label:     str
    completed: bool
    timestamp: str = ""


@dataclass
class UploadDetail:
    """Detalhe completo de um envio específico, exibido na tela admin."""
    upload_id:         str
    supplier_name:     str
    supplier_id:       str
    file_name:         str
    report_type:       str
    period:            str
    version:           int
    status:            str
    uploaded_by:       str
    sent_at:           str
    total_rows:        int
    valid_rows:        int
    invalid_rows:      int
    target_layer:      str
    is_active:         bool
    timeline:          list[ProcessingStep] = field(default_factory=list)
    validation_checks: list[ValidationCheck] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Conversão de dict → UploadRecord
# ---------------------------------------------------------------------------

def _dict_to_record(d: dict) -> UploadRecord:
    """
    Converte um dict (mock ou sessão) para UploadRecord.
    is_active: derivado do campo do dict, ou True se status == 'valid' e não especificado
               (compatibilidade com dados mock que não têm o campo).
    """
    status = d["status"]
    is_active = d.get("is_active", status == "valid")
    return UploadRecord(
        upload_id=    d["upload_id"],
        file_name=    d["file_name"],
        period=       d["period"],
        version=      d["version"],
        status=       status,
        sent_at=      d["sent_at"],
        valid_rows=   d["valid_rows"],
        invalid_rows= d["invalid_rows"],
        supplier_id=  d["supplier_id"],
        is_active=    is_active,
        report_type=  d.get("report_type", DEFAULT_REPORT_TYPE),
    )


# ---------------------------------------------------------------------------
# Detalhe extra de UP-002 (timeline + validações — dados específicos da tela)
# ---------------------------------------------------------------------------

_UPLOAD_DETAIL_EXTRA: dict[str, dict] = {
    "UP-002": {
        "report_type":  DEFAULT_REPORT_TYPE,
        "uploaded_by":  "joao.vianmaq@email.com",
        "target_layer": "TRUSTED.forecast_validated",
        "is_active":    True,
        "timeline": [
            ProcessingStep("Recebido",       completed=True, timestamp="04/05/2026 09:10"),
            ProcessingStep("Validado",        completed=True, timestamp="04/05/2026 09:11"),
            ProcessingStep("Normalizado",     completed=True, timestamp="04/05/2026 09:12"),
            ProcessingStep("Disponibilizado", completed=True, timestamp="04/05/2026 09:13"),
        ],
        "validation_checks": [
            ValidationCheck("Extensão do arquivo",  "OK", "Arquivo .xlsx aceito"),
            ValidationCheck("Colunas obrigatórias", "OK", "Todas as colunas esperadas encontradas"),
            ValidationCheck("Campos nulos",         "OK", "Nenhum campo obrigatório nulo"),
            ValidationCheck("Quantidade numérica",  "OK", "Todas as quantidades válidas"),
            ValidationCheck("Datas válidas",        "OK", "Todas as datas convertidas corretamente"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Funções de acesso
# ---------------------------------------------------------------------------

def get_supplier_uploads(
    supplier_id: str,
    include_mock: bool = True,
) -> list[UploadRecord]:
    """
    Retorna a lista de envios do fornecedor informado.

    Prioridade:
      1. Snowflake CONTROL.UPLOAD_BATCHES (fonte de verdade)
      2. Fallback: session_state.session_uploads (se Snowflake vazio)
      3. Fallback: dados mock (apenas quando DEMO_MODE=True e include_mock=True)

    Parâmetros:
        supplier_id  — ID do fornecedor (vem do session_state)
        include_mock — Se True (padrão), mescla uploads da sessão com dados mock.
                       Ignorado quando DEMO_MODE=False.
    """
    from utils.constants import DEMO_MODE
    from utils.session_state import get_session_uploads, get_cancellation

    # 1. Fonte de verdade: Snowflake
    sf_dicts = get_supplier_upload_batches(supplier_id)
    if sf_dicts:
        _upload_logger.info(
            "get_supplier_uploads: %d uploads do Snowflake para supplier_id=%s",
            len(sf_dicts), supplier_id,
        )
        return [_dict_to_record(d) for d in sf_dicts]

    # 2. Fallback: uploads da sessão
    session_records = [_dict_to_record(d) for d in get_session_uploads(supplier_id)]

    if session_records:
        _upload_logger.warning(
            "get_supplier_uploads: fallback para session_state — "
            "%d uploads para supplier_id=%s. Snowflake não retornou dados.",
            len(session_records), supplier_id,
        )

    # DEMO_MODE=False → nunca misturar dados mock, independente de include_mock
    if not include_mock or not DEMO_MODE:
        return session_records

    # 3. Fallback: dados mock (DEMO_MODE=True)
    # Períodos com upload ativo e válido na sessão
    valid_session_periods = {r.period for r in session_records if r.status == "valid"}

    # Uploads mock com ajustes de status dinâmicos
    mock_records: list[UploadRecord] = []
    for d in get_mock_uploads(supplier_id=supplier_id):
        rec = _dict_to_record(d)

        # Verificar override de cancelamento
        cancellation = get_cancellation(rec.upload_id)
        if cancellation:
            mock_records.append(UploadRecord(
                upload_id=    rec.upload_id,
                file_name=    rec.file_name,
                period=       rec.period,
                version=      rec.version,
                status=       "canceled",
                sent_at=      rec.sent_at,
                valid_rows=   rec.valid_rows,
                invalid_rows= rec.invalid_rows,
                supplier_id=  rec.supplier_id,
                is_active=    False,
                report_type=  rec.report_type,
            ))
            continue

        # Verificar se foi substituído por versão nova da sessão
        if rec.period in valid_session_periods and rec.status == "valid":
            mock_records.append(UploadRecord(
                upload_id=    rec.upload_id,
                file_name=    rec.file_name,
                period=       rec.period,
                version=      rec.version,
                status=       "replaced",
                sent_at=      rec.sent_at,
                valid_rows=   rec.valid_rows,
                invalid_rows= rec.invalid_rows,
                supplier_id=  rec.supplier_id,
                is_active=    False,
                report_type=  rec.report_type,
            ))
            continue

        mock_records.append(rec)

    return session_records + mock_records


def get_all_uploads(include_mock: bool = True) -> list[UploadRecord]:
    """
    Retorna uploads de TODOS os fornecedores (visão admin).

    Parâmetros:
        include_mock — Se True (padrão), mescla uploads da sessão com dados mock.
                       Se False, retorna apenas uploads da sessão atual.

    Aplica as mesmas regras de status dinâmico (cancelamento, substituição)
    que get_supplier_uploads(), mas sem filtrar por supplier_id.
    """
    from utils.constants import DEMO_MODE
    from utils.session_state import get_all_session_uploads, get_cancellation

    session_records = [_dict_to_record(d) for d in get_all_session_uploads()]

    # DEMO_MODE=False → nunca misturar dados mock
    if not include_mock or not DEMO_MODE:
        return session_records

    # Chaves (supplier_id, period) com upload válido na sessão
    valid_session_keys = {
        (r.supplier_id.upper(), r.period)
        for r in session_records if r.status == "valid"
    }

    mock_records: list[UploadRecord] = []
    for d in get_mock_uploads(supplier_id=None):  # todos os fornecedores
        rec = _dict_to_record(d)

        cancellation = get_cancellation(rec.upload_id)
        if cancellation:
            mock_records.append(UploadRecord(
                upload_id=    rec.upload_id,
                file_name=    rec.file_name,
                period=       rec.period,
                version=      rec.version,
                status=       "canceled",
                sent_at=      rec.sent_at,
                valid_rows=   rec.valid_rows,
                invalid_rows= rec.invalid_rows,
                supplier_id=  rec.supplier_id,
                is_active=    False,
                report_type=  rec.report_type,
            ))
            continue

        if (rec.supplier_id.upper(), rec.period) in valid_session_keys and rec.status == "valid":
            mock_records.append(UploadRecord(
                upload_id=    rec.upload_id,
                file_name=    rec.file_name,
                period=       rec.period,
                version=      rec.version,
                status=       "replaced",
                sent_at=      rec.sent_at,
                valid_rows=   rec.valid_rows,
                invalid_rows= rec.invalid_rows,
                supplier_id=  rec.supplier_id,
                is_active=    False,
                report_type=  rec.report_type,
            ))
            continue

        mock_records.append(rec)

    return session_records + mock_records


def get_admin_status_rows(period: str | None = None) -> list[dict]:
    """
    Constrói a tabela de status por fornecedor para o painel administrativo.

    Prioridade: Snowflake (CONTROL.SUPPLIERS + CONTROL.UPLOAD_BATCHES) → fallback session.

    Parâmetros:
        period — período de referência no formato "YYYY-MM".
                 Se None, usa o período da janela aberta.

    Retorno: list[dict] com chaves:
        name, code, period, status, last, version, errors, upload_id
    """
    from services.mock_data_service import get_current_open_window
    from services.snowflake_service import get_snowflake_session

    if period is None:
        window = get_current_open_window()
        period = window["period"] if window else None

    current_period = period or ""

    # --- Tentar Snowflake ---
    session = get_snowflake_session()
    if session is not None:
        try:
            sf_rows = _build_admin_rows_from_snowflake(session, current_period)
            if sf_rows is not None:
                _upload_logger.info(
                    "get_admin_status_rows: %d linhas do Snowflake para period=%s",
                    len(sf_rows), current_period,
                )
                return sf_rows
        except Exception as exc:
            _upload_logger.error(
                "get_admin_status_rows: falha Snowflake, usando fallback. erro=%s", exc,
            )

    # --- Fallback: lógica antiga baseada em session_state ---
    _upload_logger.warning(
        "get_admin_status_rows: fallback session_state para period=%s", current_period,
    )
    return _build_admin_rows_from_session(current_period)


def _build_admin_rows_from_snowflake(session, period: str) -> list[dict]:
    """
    Constrói status rows diretamente do Snowflake.
    JOIN CONTROL.SUPPLIERS com CONTROL.UPLOAD_BATCHES filtrado por período.
    """
    import pandas as pd

    safe_period = period.replace("'", "''") if period else ""

    # Buscar fornecedores ativos e seu upload mais recente no período
    query = f"""
        WITH latest_uploads AS (
            SELECT
                SUPPLIER_ID,
                UPLOAD_ID,
                STATUS,
                IS_ACTIVE,
                VERSION,
                INVALID_ROWS,
                UPLOADED_AT,
                ROW_NUMBER() OVER (
                    PARTITION BY SUPPLIER_ID
                    ORDER BY
                        CASE WHEN STATUS = 'VALID' AND IS_ACTIVE = TRUE THEN 0
                             WHEN STATUS = 'INVALID' THEN 1
                             ELSE 2
                        END,
                        UPLOADED_AT DESC
                ) AS RN
            FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
            WHERE REFERENCE_PERIOD = '{safe_period}'
        )
        SELECT
            s.SUPPLIER_NAME,
            s.SUPPLIER_CODE,
            lu.UPLOAD_ID,
            lu.STATUS AS UPLOAD_STATUS,
            lu.IS_ACTIVE,
            lu.VERSION,
            lu.INVALID_ROWS,
            lu.UPLOADED_AT
        FROM {_DATABASE}.CONTROL.SUPPLIERS s
        LEFT JOIN latest_uploads lu
            ON s.SUPPLIER_CODE = lu.SUPPLIER_ID AND lu.RN = 1
        WHERE s.STATUS = 'active'
        ORDER BY s.SUPPLIER_CODE
    """

    df = session.sql(query).to_pandas()
    if df is None:
        return None

    rows: list[dict] = []
    for _, row in df.iterrows():
        name = str(row["SUPPLIER_NAME"])
        code = str(row["SUPPLIER_CODE"])
        upload_id = row["UPLOAD_ID"]
        upload_status = str(row["UPLOAD_STATUS"]) if row["UPLOAD_STATUS"] else None

        if upload_status == "VALID" and row["IS_ACTIVE"]:
            # Fornecedor com forecast válido ativo
            uploaded_at = row["UPLOADED_AT"]
            try:
                ts = pd.Timestamp(uploaded_at)
                last = ts.strftime("%d/%m/%Y %H:%M")
            except Exception:
                last = str(uploaded_at)[:16] if uploaded_at else "—"

            rows.append({
                "name":      name,
                "code":      code,
                "period":    period,
                "status":    "valid",
                "last":      last,
                "version":   _safe_int(row["VERSION"], 1),
                "errors":    0,
                "upload_id": str(upload_id) if upload_id else None,
            })
        elif upload_status == "INVALID":
            # Upload inválido no período: fornecedor fica como Pendente.
            # Erros são responsabilidade do fornecedor — não exibir no admin.
            rows.append({
                "name":      name,
                "code":      code,
                "period":    period,
                "status":    "pending",
                "last":      "—",
                "version":   "—",
                "errors":    "—",
                "upload_id": None,
            })
        else:
            # Sem upload no período → Pendente
            rows.append({
                "name":      name,
                "code":      code,
                "period":    period,
                "status":    "pending",
                "last":      "—",
                "version":   "—",
                "errors":    "—",
                "upload_id": None,
            })

    return rows


def _build_admin_rows_from_session(period: str) -> list[dict]:
    """Fallback: lógica antiga baseada em session_state/mock."""
    from utils.dates import to_period_ym
    from utils.session_state import get_session_validated_forecasts
    from services.supplier_service import get_all_suppliers

    current_period = period
    valid_forecasts = get_session_validated_forecasts()
    all_ups = get_all_uploads(include_mock=True)

    rows: list[dict] = []
    for s_rec in get_all_suppliers():
        if s_rec.status == "inactive":
            continue

        code_upper = s_rec.code.upper()

        sup_forecasts = [
            f for f in valid_forecasts
            if str(f.get("supplier_id", "")).upper() == code_upper
            and (
                not current_period
                or to_period_ym(str(f.get("forecast_period", ""))) == current_period
            )
        ]

        if sup_forecasts:
            try:
                latest_f = max(sup_forecasts, key=lambda f: str(f.get("uploaded_at", "")))
            except (ValueError, TypeError):
                latest_f = sup_forecasts[0]

            rows.append({
                "name": s_rec.name, "code": s_rec.code, "period": current_period or "—",
                "status": "valid", "last": str(latest_f.get("uploaded_at", "—")),
                "version": int(latest_f.get("upload_version", 1)),
                "errors": 0, "upload_id": latest_f.get("upload_id"),
            })
            continue

        sup_invalid = [
            u for u in all_ups
            if u.supplier_id.upper() == code_upper and u.status == "invalid"
            and (not current_period or to_period_ym(u.period) == current_period)
        ]

        if sup_invalid:
            ref = sup_invalid[0]
            rows.append({
                "name": s_rec.name, "code": s_rec.code,
                "period": current_period or ref.period, "status": "pending",
                "last": ref.sent_at, "version": "—", "errors": "—",
                "upload_id": ref.upload_id,
            })
            continue

        rows.append({
            "name": s_rec.name, "code": s_rec.code, "period": current_period or "—",
            "status": "pending", "last": "—", "version": "—", "errors": "—",
            "upload_id": None,
        })

    return rows


def get_canceled_uploads_count(period: str) -> int:
    """
    Conta uploads válidos que foram cancelados no período informado.

    Prioridade: Snowflake → fallback session_state.

    Retorna o número de upload_ids distintos cancelados no período.
    """
    from services.snowflake_service import get_snowflake_session

    # --- Tentar Snowflake ---
    session = get_snowflake_session()
    if session is not None:
        try:
            safe_period = period.replace("'", "''") if period else ""
            df = session.sql(f"""
                SELECT COUNT(DISTINCT UPLOAD_ID) AS CNT
                FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
                WHERE STATUS = 'CANCELLED'
                  AND REFERENCE_PERIOD = '{safe_period}'
            """).to_pandas()
            if df is not None and not df.empty:
                return int(df.iloc[0]["CNT"])
        except Exception as exc:
            _upload_logger.warning(
                "get_canceled_uploads_count: falha Snowflake, usando fallback. erro=%s", exc,
            )

    # --- Fallback: session_state ---
    import streamlit as st
    from utils.dates import to_period_ym
    from utils.session_state import get_all_session_uploads

    all_ups = get_all_session_uploads()
    canceled_ids = {
        u["upload_id"]
        for u in all_ups
        if u.get("status") == "canceled"
    }
    if not canceled_ids:
        return 0

    all_forecasts = st.session_state.get("session_validated_forecasts", [])
    matched: set[str] = set()
    for f in all_forecasts:
        uid = f.get("upload_id")
        if uid in canceled_ids and uid not in matched:
            if to_period_ym(str(f.get("forecast_period", ""))) == period:
                matched.add(uid)

    return len(matched)


def get_available_periods_from_snowflake() -> list[str]:
    """
    Retorna períodos distintos presentes em UPLOAD_BATCHES, ordenados DESC.
    Exclui valores nulos ou '—'. Formato: YYYY-MM.
    """
    from services.snowflake_service import get_snowflake_session

    session = get_snowflake_session()
    if session is None:
        return []

    try:
        df = session.sql(f"""
            SELECT DISTINCT REFERENCE_PERIOD
            FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
            WHERE REFERENCE_PERIOD IS NOT NULL
              AND REFERENCE_PERIOD != '—'
              AND REFERENCE_PERIOD != ''
            ORDER BY REFERENCE_PERIOD DESC
        """).to_pandas()
        if df is not None and not df.empty:
            return df["REFERENCE_PERIOD"].tolist()
    except Exception as exc:
        _upload_logger.warning(
            "get_available_periods_from_snowflake: falha. erro=%s", exc,
        )

    return []


def can_cancel(record: UploadRecord) -> bool:
    """
    Retorna True se o envio pode ser cancelado logicamente.

    Condições:
    1. is_active = True  (é a versão vigente para a chave)
    2. status == "valid" (uploads inválidos/substituídos não podem ser cancelados)
    3. período dentro da janela de envio aberta (comparação normalizada YYYY-MM)

    Normaliza o período antes de comparar via to_period_ym().
    Fallback: se period="—" no upload, verifica forecast_period em
    session_validated_forecasts para o upload_id correspondente.
    """
    from utils.dates import to_period_ym
    window = get_current_open_window()
    if not window:
        return False
    if not (record.is_active and record.status == "valid"):
        return False

    # Comparação principal via período do upload record
    if to_period_ym(record.period) == window["period"]:
        return True

    # Fallback: período do upload pode ser "—" quando a extração falhou.
    # Verificar o forecast_period das linhas em session_validated_forecasts.
    import streamlit as st
    all_forecasts = st.session_state.get("session_validated_forecasts", [])
    for f in all_forecasts:
        if f.get("upload_id") == record.upload_id:
            if to_period_ym(str(f.get("forecast_period", ""))) == window["period"]:
                return True

    return False


def get_upload_detail(upload_id: str) -> Optional[UploadDetail]:
    """
    Retorna o detalhe completo de um upload pelo seu ID.
    Prioridade: Snowflake CONTROL.UPLOAD_BATCHES → session_state → mock.
    """
    from services.snowflake_service import get_snowflake_session
    from utils.session_state import get_session_upload_by_id
    import streamlit as st
    import pandas as pd

    # --- 1. Fonte de verdade: Snowflake ---
    session = get_snowflake_session()
    if session is not None:
        try:
            safe_id = upload_id.replace("'", "''")
            df = session.sql(f"""
                SELECT UPLOAD_ID, SUPPLIER_ID, SUPPLIER_NAME, FILE_NAME,
                       REPORT_TYPE, REFERENCE_PERIOD, VERSION, STATUS, IS_ACTIVE,
                       UPLOADED_BY, UPLOADED_AT, TOTAL_ROWS, VALID_ROWS, INVALID_ROWS
                FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
                WHERE UPLOAD_ID = '{safe_id}'
            """).to_pandas()

            if df is not None and not df.empty:
                row = df.iloc[0]
                raw_status = str(row["STATUS"]).lower()
                if raw_status == "cancelled":
                    raw_status = "canceled"

                uploaded_at = row["UPLOADED_AT"]
                try:
                    ts = pd.Timestamp(uploaded_at)
                    sent_at = ts.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    sent_at = str(uploaded_at)[:16] if uploaded_at else "—"

                _upload_logger.info(
                    "get_upload_detail: encontrado no Snowflake — upload_id=%s", upload_id,
                )
                return UploadDetail(
                    upload_id=         str(row["UPLOAD_ID"]),
                    supplier_name=     str(row["SUPPLIER_NAME"]),
                    supplier_id=       str(row["SUPPLIER_ID"]),
                    file_name=         str(row["FILE_NAME"]),
                    report_type=       str(row["REPORT_TYPE"]),
                    period=            str(row["REFERENCE_PERIOD"]),
                    version=           _safe_int(row["VERSION"], 1),
                    status=            raw_status,
                    uploaded_by=       str(row["UPLOADED_BY"]) if row["UPLOADED_BY"] else "—",
                    sent_at=           sent_at,
                    total_rows=        _safe_int(row["TOTAL_ROWS"]),
                    valid_rows=        _safe_int(row["VALID_ROWS"]),
                    invalid_rows=      _safe_int(row["INVALID_ROWS"]),
                    target_layer=      "TRUSTED.forecast_validated",
                    is_active=         bool(row["IS_ACTIVE"]),
                    timeline=          [],
                    validation_checks= [],
                )
        except Exception as exc:
            _upload_logger.warning(
                "get_upload_detail: falha Snowflake, usando fallback. erro=%s", exc,
            )

    # --- 2. Fallback: uploads registrados na sessão atual ---
    session_rec = get_session_upload_by_id(upload_id)
    if session_rec is not None:
        _upload_logger.info(
            "get_upload_detail: fallback session_state — upload_id=%s", upload_id,
        )
        return UploadDetail(
            upload_id=         session_rec["upload_id"],
            supplier_name=     session_rec.get("supplier_name", "—"),
            supplier_id=       session_rec.get("supplier_id", "—"),
            file_name=         session_rec.get("file_name", "—"),
            report_type=       session_rec.get("report_type", DEFAULT_REPORT_TYPE),
            period=            session_rec.get("period", "—"),
            version=           session_rec.get("version", 1),
            status=            session_rec.get("status", "—"),
            uploaded_by=       session_rec.get("uploaded_by") or "—",
            sent_at=           session_rec.get("sent_at", "—"),
            total_rows=        session_rec.get("valid_rows", 0) + session_rec.get("invalid_rows", 0),
            valid_rows=        session_rec.get("valid_rows", 0),
            invalid_rows=      session_rec.get("invalid_rows", 0),
            target_layer=      "TRUSTED.forecast_validated",
            is_active=         session_rec.get("is_active", False),
            timeline=          [],
            validation_checks= [],
        )

    # --- 3. Fallback: dados mock ---
    raw = get_mock_upload_by_id(upload_id)
    if raw is None:
        return None

    extra = _UPLOAD_DETAIL_EXTRA.get(upload_id, {})

    return UploadDetail(
        upload_id=         raw["upload_id"],
        supplier_name=     raw["supplier_name"],
        supplier_id=       raw["supplier_id"],
        file_name=         raw["file_name"],
        report_type=       extra.get("report_type", DEFAULT_REPORT_TYPE),
        period=            raw["period"],
        version=           raw["version"],
        status=            raw["status"],
        uploaded_by=       extra.get("uploaded_by", "—"),
        sent_at=           raw["sent_at"],
        total_rows=        raw["valid_rows"] + raw["invalid_rows"],
        valid_rows=        raw["valid_rows"],
        invalid_rows=      raw["invalid_rows"],
        target_layer=      extra.get("target_layer", "TRUSTED.forecast_validated"),
        is_active=         extra.get("is_active", raw["status"] == "valid"),
        timeline=          extra.get("timeline", []),
        validation_checks= extra.get("validation_checks", []),
    )


# ---------------------------------------------------------------------------
# Persistência em Snowflake — CONTROL.UPLOAD_BATCHES
# ---------------------------------------------------------------------------

import math
import uuid

from utils.logger import get_logger

_upload_logger = get_logger(__name__)

_DATABASE = "KBI_DATA_JOURNEY_DEV_DB"


def _safe_int(value, default: int = 0) -> int:
    """Converte valor para int de forma segura, tratando None, NaN e strings vazias."""
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def persist_upload_batch(
    *,
    supplier_id: str,
    supplier_name: str,
    user_id: str,
    file_name: str,
    reference_period: str,
    status: str,
    valid_rows: int,
    invalid_rows: int,
    uploaded_by: str,
    report_type: str = DEFAULT_REPORT_TYPE,
    window_id: str | None = None,
    uploaded_at: str | None = None,
) -> dict | None:
    """
    Persiste um registro de upload em CONTROL.UPLOAD_BATCHES no Snowflake.

    Lógica de versionamento:
      - Calcula version_key = supplier_id|report_type|reference_period
      - Calcula version = MAX(version) + 1 para a mesma version_key
      - Se status=VALID: marca uploads anteriores ativos da mesma key como REPLACED

    Retorna:
        dict {"upload_id": str, "version": int} se INSERT bem-sucedido, None se falhar.
    """
    from services.snowflake_service import get_snowflake_session

    _upload_logger.info(
        "persist_upload_batch: supplier=%s, period=%s, status=%s, file=%s",
        supplier_id, reference_period, status, file_name,
    )

    session = get_snowflake_session()
    if session is None:
        _upload_logger.error(
            "persist_upload_batch: sessão Snowflake indisponível."
        )
        return None

    upload_id = str(uuid.uuid4())
    version_key = f"{supplier_id.upper()}|{report_type.strip()}|{reference_period.strip()}"
    status_upper = status.upper()  # VALID / INVALID
    is_active = status_upper == "VALID"
    total_rows = valid_rows + invalid_rows

    # 1. Calcular versão
    # Uploads INVALID recebem VERSION=0 (sentinela — não consomem numeração).
    # Uploads VALID incrementam com base em versões reais (VALID/REPLACED/CANCELLED).
    if not is_active:
        next_version = 0
    else:
        try:
            version_df = session.sql(f"""
                SELECT COALESCE(MAX(VERSION), 0) AS MAX_V
                FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
                WHERE VERSION_KEY = '{version_key.replace("'", "''")}'
                  AND STATUS IN ('VALID', 'REPLACED', 'CANCELLED')
            """).to_pandas()
            next_version = int(version_df.iloc[0]["MAX_V"]) + 1 if version_df is not None and not version_df.empty else 1
        except Exception as exc:
            _upload_logger.error(
                "Falha ao calcular versão: %s", exc
            )
            return None

    # 2. Se VALID, marcar uploads anteriores como REPLACED
    if is_active:
        try:
            session.sql(f"""
                UPDATE {_DATABASE}.CONTROL.UPLOAD_BATCHES
                SET STATUS = 'REPLACED', IS_ACTIVE = FALSE
                WHERE VERSION_KEY = '{version_key.replace("'", "''")}'
                  AND IS_ACTIVE = TRUE
            """).collect()
        except Exception as exc:
            _upload_logger.error(
                "Falha ao marcar uploads anteriores como REPLACED: %s", exc
            )
            return None

    # 3. INSERT do novo registro
    safe_name = supplier_name.replace("'", "''")
    safe_file = file_name.replace("'", "''")
    safe_by = uploaded_by.replace("'", "''")
    safe_user_id = user_id.replace("'", "''") if user_id else supplier_id
    window_val = f"'{window_id}'" if window_id else "NULL"

    # Se uploaded_at fornecido, incluir na coluna; senão Snowflake usa CURRENT_TIMESTAMP()
    if uploaded_at:
        ts_col = ", UPLOADED_AT"
        ts_val = f", '{uploaded_at}'"
    else:
        ts_col = ""
        ts_val = ""

    insert_sql = f"""
        INSERT INTO {_DATABASE}.CONTROL.UPLOAD_BATCHES (
            UPLOAD_ID, SUPPLIER_ID, SUPPLIER_NAME, USER_ID,
            REPORT_TYPE, REFERENCE_PERIOD, VERSION, VERSION_KEY,
            STATUS, IS_ACTIVE, FILE_NAME,
            TOTAL_ROWS, VALID_ROWS, INVALID_ROWS,
            UPLOADED_BY, WINDOW_ID{ts_col}
        ) VALUES (
            '{upload_id}', '{supplier_id}', '{safe_name}', '{safe_user_id}',
            '{report_type}', '{reference_period}', {next_version}, '{version_key.replace("'", "''")}',
            '{status_upper}', {is_active}, '{safe_file}',
            {total_rows}, {valid_rows}, {invalid_rows},
            '{safe_by}', {window_val}{ts_val}
        )
    """

    try:
        session.sql(insert_sql).collect()
    except Exception as exc:
        _upload_logger.error(
            "persist_upload_batch INSERT falhou.\n"
            "  SQL: %s\n"
            "  erro: %s\n"
            "  tipo: %s",
            insert_sql[:500], exc, type(exc).__name__,
        )
        return None

    _upload_logger.info(
        "Upload persistido: id=%s, supplier=%s, period=%s, "
        "version=%d, status=%s, valid_rows=%d, invalid_rows=%d",
        upload_id, supplier_id, reference_period, next_version, status_upper,
        valid_rows, invalid_rows,
    )

    return {"upload_id": upload_id, "version": next_version}


# ---------------------------------------------------------------------------
# Persistência em Snowflake — CONTROL.VALIDATION_ERRORS
# ---------------------------------------------------------------------------

def persist_validation_errors(
    upload_id: str,
    errors: list[dict],
) -> int:
    """
    Persiste erros de validação em CONTROL.VALIDATION_ERRORS.

    Parâmetros:
        upload_id — UUID retornado por persist_upload_batch()
        errors   — lista de dicts com chaves:
                   linha, coluna, valor_informado, erro, orientacao_correcao

    Retorna:
        Quantidade de erros inseridos com sucesso (0 se falhar ou lista vazia).
    """
    from services.snowflake_service import get_snowflake_session

    if not errors:
        _upload_logger.info(
            "persist_validation_errors: lista vazia — nada a persistir."
        )
        return 0

    _upload_logger.info(
        "persist_validation_errors: início — upload_id=%s, total_erros=%d",
        upload_id, len(errors),
    )

    session = get_snowflake_session()
    if session is None:
        _upload_logger.error(
            "persist_validation_errors: sessão Snowflake indisponível."
        )
        return 0

    # Construir VALUES multi-row
    value_rows: list[str] = []
    for err in errors:
        error_id = str(uuid.uuid4())
        row_number = int(err.get("linha", 0))
        column_name = str(err.get("coluna", ""))[:200].replace("'", "''")
        value_informed = str(err.get("valor_informado", "") or "")[:1000].replace("'", "''")
        error_type = str(err.get("erro", ""))[:100].replace("'", "''")
        correction = str(err.get("orientacao_correcao", "") or "")[:500].replace("'", "''")

        value_rows.append(
            f"('{error_id}', '{upload_id}', {row_number}, "
            f"'{column_name}', '{value_informed}', '{error_type}', '{correction}')"
        )

    insert_sql = f"""
        INSERT INTO {_DATABASE}.CONTROL.VALIDATION_ERRORS (
            ERROR_ID, UPLOAD_ID, ROW_NUMBER,
            COLUMN_NAME, VALUE_INFORMED, ERROR_TYPE, CORRECTION_GUIDANCE
        ) VALUES
        {', '.join(value_rows)}
    """

    try:
        session.sql(insert_sql).collect()
    except Exception as exc:
        _upload_logger.error(
            "persist_validation_errors: INSERT falhou.\n"
            "  upload_id: %s\n"
            "  erros_tentados: %d\n"
            "  erro: %s\n"
            "  tipo: %s",
            upload_id, len(errors), exc, type(exc).__name__,
        )
        return 0

    _upload_logger.info(
        "persist_validation_errors: sucesso — %d erros inseridos para upload_id=%s",
        len(errors), upload_id,
    )
    return len(errors)


# ---------------------------------------------------------------------------
# Leitura de erros persistidos — CONTROL.VALIDATION_ERRORS
# ---------------------------------------------------------------------------

def get_validation_errors(upload_id: str) -> list[dict]:
    """
    Busca erros de validação no Snowflake para o upload_id informado.

    Retorna lista de dicts com chaves no formato esperado pela UI:
        linha, coluna, valor_informado, erro, orientacao_correcao

    Retorna lista vazia se não encontrar erros ou se a sessão estiver indisponível.
    """
    from services.snowflake_service import get_snowflake_session

    _upload_logger.info(
        "get_validation_errors: consultando upload_id=%s", upload_id,
    )

    session = get_snowflake_session()
    if session is None:
        _upload_logger.error(
            "get_validation_errors: sessão Snowflake indisponível."
        )
        return []

    safe_id = upload_id.replace("'", "''")
    query = f"""
        SELECT ROW_NUMBER, COLUMN_NAME, VALUE_INFORMED,
               ERROR_TYPE, CORRECTION_GUIDANCE
        FROM {_DATABASE}.CONTROL.VALIDATION_ERRORS
        WHERE UPLOAD_ID = '{safe_id}'
        ORDER BY ROW_NUMBER
    """

    try:
        df = session.sql(query).to_pandas()
    except Exception as exc:
        _upload_logger.error(
            "get_validation_errors: falha na query.\n"
            "  upload_id: %s\n"
            "  erro: %s\n"
            "  tipo: %s",
            upload_id, exc, type(exc).__name__,
        )
        return []

    if df is None or df.empty:
        _upload_logger.info(
            "get_validation_errors: nenhum erro encontrado para upload_id=%s",
            upload_id,
        )
        return []

    # Mapear colunas Snowflake → formato esperado pela UI
    results: list[dict] = []
    for _, row in df.iterrows():
        results.append({
            "linha":               _safe_int(row["ROW_NUMBER"]),
            "coluna":              str(row["COLUMN_NAME"]),
            "valor_informado":     str(row["VALUE_INFORMED"]) if row["VALUE_INFORMED"] else "",
            "erro":                str(row["ERROR_TYPE"]),
            "orientacao_correcao": str(row["CORRECTION_GUIDANCE"]) if row["CORRECTION_GUIDANCE"] else "",
        })

    _upload_logger.info(
        "get_validation_errors: %d erros retornados para upload_id=%s",
        len(results), upload_id,
    )
    return results


# ---------------------------------------------------------------------------
# Leitura de uploads do fornecedor — CONTROL.UPLOAD_BATCHES
# ---------------------------------------------------------------------------

def get_supplier_upload_batches(supplier_id: str) -> list[dict]:
    """
    Busca uploads do fornecedor em CONTROL.UPLOAD_BATCHES no Snowflake.

    Retorna list[dict] compatível com _dict_to_record():
        upload_id, file_name, period, version, status, sent_at,
        valid_rows, invalid_rows, supplier_id, is_active, report_type

    Ordenado por UPLOADED_AT DESC (mais recente primeiro).
    Retorna lista vazia se não encontrar ou se a sessão estiver indisponível.
    """
    from services.snowflake_service import get_snowflake_session

    _upload_logger.info(
        "get_supplier_upload_batches: consultando supplier_id=%s", supplier_id,
    )

    session = get_snowflake_session()
    if session is None:
        _upload_logger.error(
            "get_supplier_upload_batches: sessão Snowflake indisponível."
        )
        return []

    safe_id = supplier_id.replace("'", "''").upper()
    query = f"""
        SELECT UPLOAD_ID, SUPPLIER_ID, FILE_NAME, REFERENCE_PERIOD,
               VERSION, STATUS, IS_ACTIVE, REPORT_TYPE,
               VALID_ROWS, INVALID_ROWS, UPLOADED_AT
        FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
        WHERE SUPPLIER_ID = '{safe_id}'
        ORDER BY UPLOADED_AT DESC
    """

    try:
        df = session.sql(query).to_pandas()
    except Exception as exc:
        _upload_logger.error(
            "get_supplier_upload_batches: falha na query.\n"
            "  supplier_id: %s\n"
            "  erro: %s\n"
            "  tipo: %s",
            supplier_id, exc, type(exc).__name__,
        )
        return []

    if df is None or df.empty:
        _upload_logger.info(
            "get_supplier_upload_batches: nenhum upload encontrado para supplier_id=%s",
            supplier_id,
        )
        return []

    # Mapear colunas Snowflake → formato dict compatível com _dict_to_record
    results: list[dict] = []
    for _, row in df.iterrows():
        # Status: VALID→valid, INVALID→invalid, REPLACED→replaced, CANCELLED→canceled
        raw_status = str(row["STATUS"]).lower()
        if raw_status == "cancelled":
            raw_status = "canceled"

        # UPLOADED_AT → "DD/MM/AAAA HH:MM"
        uploaded_at = row["UPLOADED_AT"]
        try:
            import pandas as pd
            ts = pd.Timestamp(uploaded_at)
            sent_at = ts.strftime("%d/%m/%Y %H:%M")
        except Exception:
            sent_at = str(uploaded_at)[:16] if uploaded_at else "—"

        results.append({
            "upload_id":    str(row["UPLOAD_ID"]),
            "file_name":    str(row["FILE_NAME"]),
            "period":       str(row["REFERENCE_PERIOD"]),
            "version":      _safe_int(row["VERSION"], 1),
            "status":       raw_status,
            "sent_at":      sent_at,
            "valid_rows":   _safe_int(row["VALID_ROWS"]),
            "invalid_rows": _safe_int(row["INVALID_ROWS"]),
            "supplier_id":  str(row["SUPPLIER_ID"]),
            "is_active":    bool(row["IS_ACTIVE"]),
            "report_type":  str(row["REPORT_TYPE"]),
        })

    _upload_logger.info(
        "get_supplier_upload_batches: %d uploads retornados para supplier_id=%s",
        len(results), supplier_id,
    )
    return results


# ---------------------------------------------------------------------------
# Cancelamento persistido — CONTROL.UPLOAD_BATCHES
# ---------------------------------------------------------------------------

def persist_cancel_upload(
    upload_id: str,
    supplier_id: str,
    cancelled_by: str = "",
    cancel_reason: str = "",
) -> bool:
    """
    Cancela logicamente um upload em CONTROL.UPLOAD_BATCHES.

    Validações (via WHERE):
      - Upload existe com UPLOAD_ID informado
      - Pertence ao SUPPLIER_ID informado
      - STATUS = 'VALID' e IS_ACTIVE = TRUE

    UPDATE aplicado:
      - STATUS = 'CANCELLED'
      - IS_ACTIVE = FALSE
      - CANCELLED_AT = CURRENT_TIMESTAMP()
      - CANCELLED_BY = cancelled_by
      - CANCELLATION_REASON = cancel_reason

    Retorna True se o cancelamento foi persistido, False caso contrário.
    """
    from services.snowflake_service import get_snowflake_session

    _upload_logger.info(
        "persist_cancel_upload: início — upload_id=%s, supplier_id=%s, by=%s",
        upload_id, supplier_id, cancelled_by,
    )

    session = get_snowflake_session()
    if session is None:
        _upload_logger.error(
            "persist_cancel_upload: sessão Snowflake indisponível."
        )
        return False

    safe_upload_id = upload_id.replace("'", "''")
    safe_supplier_id = supplier_id.replace("'", "''").upper()
    safe_by = cancelled_by.replace("'", "''") if cancelled_by else ""
    safe_reason = cancel_reason.replace("'", "''") if cancel_reason else ""

    # Pré-verificação: upload deve existir, pertencer ao supplier, ser VALID e ACTIVE
    try:
        pre_df = session.sql(f"""
            SELECT STATUS, IS_ACTIVE
            FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
            WHERE UPLOAD_ID = '{safe_upload_id}'
              AND SUPPLIER_ID = '{safe_supplier_id}'
        """).to_pandas()

        if pre_df is None or pre_df.empty:
            _upload_logger.error(
                "persist_cancel_upload: upload_id=%s não encontrado para supplier_id=%s.",
                upload_id, supplier_id,
            )
            return False

        current_status = str(pre_df.iloc[0]["STATUS"])
        current_active = bool(pre_df.iloc[0]["IS_ACTIVE"])

        if current_status != "VALID" or not current_active:
            _upload_logger.error(
                "persist_cancel_upload: upload não é cancelável. "
                "status=%s, is_active=%s (requer VALID + TRUE).",
                current_status, current_active,
            )
            return False

    except Exception as exc:
        _upload_logger.error(
            "persist_cancel_upload: falha na pré-verificação.\n"
            "  upload_id: %s\n"
            "  erro: %s",
            upload_id, exc,
        )
        return False

    update_sql = f"""
        UPDATE {_DATABASE}.CONTROL.UPLOAD_BATCHES
        SET STATUS = 'CANCELLED',
            IS_ACTIVE = FALSE,
            CANCELLED_AT = CURRENT_TIMESTAMP(),
            CANCELLED_BY = '{safe_by}',
            CANCELLATION_REASON = '{safe_reason}'
        WHERE UPLOAD_ID = '{safe_upload_id}'
          AND SUPPLIER_ID = '{safe_supplier_id}'
          AND STATUS = 'VALID'
          AND IS_ACTIVE = TRUE
    """

    try:
        session.sql(update_sql).collect()
    except Exception as exc:
        _upload_logger.error(
            "persist_cancel_upload: UPDATE falhou.\n"
            "  upload_id: %s\n"
            "  erro: %s\n"
            "  tipo: %s",
            upload_id, exc, type(exc).__name__,
        )
        return False

    # Verificar se o UPDATE realmente alterou o registro
    try:
        check_df = session.sql(f"""
            SELECT STATUS, IS_ACTIVE
            FROM {_DATABASE}.CONTROL.UPLOAD_BATCHES
            WHERE UPLOAD_ID = '{safe_upload_id}'
        """).to_pandas()

        if check_df is None or check_df.empty:
            _upload_logger.error(
                "persist_cancel_upload: upload_id=%s não encontrado após UPDATE.",
                upload_id,
            )
            return False

        new_status = str(check_df.iloc[0]["STATUS"])
        new_active = bool(check_df.iloc[0]["IS_ACTIVE"])

        if new_status != "CANCELLED" or new_active is True:
            _upload_logger.error(
                "persist_cancel_upload: UPDATE não surtiu efeito. "
                "status=%s, is_active=%s. "
                "Possível causa: upload não era VALID/ACTIVE ou não pertence ao supplier.",
                new_status, new_active,
            )
            return False

    except Exception as exc:
        _upload_logger.error(
            "persist_cancel_upload: falha na verificação pós-UPDATE.\n"
            "  upload_id: %s\n"
            "  erro: %s",
            upload_id, exc,
        )
        return False

    _upload_logger.info(
        "persist_cancel_upload: sucesso — upload_id=%s cancelado por '%s'.",
        upload_id, cancelled_by,
    )
    return True


# ---------------------------------------------------------------------------
# Persistência em Snowflake — TRUSTED.FORECAST_VALIDATED
# ---------------------------------------------------------------------------

def persist_validated_forecast(
    upload_id: str,
    supplier_id: str,
    supplier_name: str,
    upload_version: int,
    source_file_name: str,
    staging_df,
) -> int:
    """
    Persiste linhas normalizadas de um upload válido em TRUSTED.FORECAST_VALIDATED.

    Antes de inserir, desativa (IS_ACTIVE=FALSE) linhas anteriores do mesmo
    fornecedor para os mesmos forecast_period que estão sendo inseridos.

    Parâmetros:
        upload_id        — UUID retornado por persist_upload_batch()
        supplier_id      — ID do fornecedor
        supplier_name    — Nome do fornecedor
        upload_version   — Versão do upload
        source_file_name — Nome do arquivo original
        staging_df       — DataFrame com colunas do esquema alvo (forecast_service)

    Retorna:
        Quantidade de linhas inseridas (0 se falhar ou DataFrame vazio).
    """
    import pandas as pd
    from services.snowflake_service import get_snowflake_session

    if staging_df is None or len(staging_df) == 0:
        _upload_logger.info(
            "persist_validated_forecast: DataFrame vazio — nada a persistir."
        )
        return 0

    _upload_logger.info(
        "persist_validated_forecast: início — upload_id=%s, supplier_id=%s, linhas=%d",
        upload_id, supplier_id, len(staging_df),
    )

    session = get_snowflake_session()
    if session is None:
        _upload_logger.error(
            "persist_validated_forecast: sessão Snowflake indisponível."
        )
        return 0

    # Extrair períodos únicos para desativar linhas anteriores
    periods = staging_df["forecast_period"].dropna().unique().tolist()
    safe_supplier = supplier_id.replace("'", "''").upper()

    # Desativar linhas anteriores do mesmo fornecedor para os mesmos períodos
    if periods:
        period_values = ", ".join(
            f"'{_to_date_str(str(p))}'" for p in periods
        )
        deactivate_sql = f"""
            UPDATE {_DATABASE}.TRUSTED.FORECAST_VALIDATED
            SET IS_ACTIVE = FALSE
            WHERE SUPPLIER_ID = '{safe_supplier}'
              AND FORECAST_PERIOD IN ({period_values})
              AND IS_ACTIVE = TRUE
              AND UPLOAD_ID != '{upload_id.replace("'", "''")}'
        """
        try:
            session.sql(deactivate_sql).collect()
            _upload_logger.info(
                "persist_validated_forecast: linhas anteriores desativadas para "
                "supplier=%s, periods=%s",
                supplier_id, periods,
            )
        except Exception as exc:
            _upload_logger.warning(
                "persist_validated_forecast: falha ao desativar linhas anteriores: %s",
                exc,
            )
            # Não bloqueia o INSERT — linhas antigas ficarão ativas até correção

    # Construir VALUES multi-row
    value_rows: list[str] = []
    for _, row in staging_df.iterrows():
        row_id = str(uuid.uuid4())
        branch = str(row.get("branch", ""))[:255].replace("'", "''")
        mat_code = str(row.get("material_code", ""))[:100].replace("'", "''")
        mat_desc = str(row.get("material_description", "") or "")[:500].replace("'", "''")
        forecast_period = _to_date_str(str(row.get("forecast_period", "")))
        forecast_qty = _to_numeric(row.get("forecast_quantity", 0))
        safe_name = supplier_name[:255].replace("'", "''")
        safe_file = source_file_name[:500].replace("'", "''")
        uploaded_at = str(row.get("uploaded_at", ""))

        value_rows.append(
            f"('{row_id}', '{safe_supplier}', '{safe_name}', '{branch}', "
            f"'{mat_code}', '{mat_desc}', '{forecast_period}', {forecast_qty}, "
            f"'{upload_id}', {upload_version}, '{uploaded_at}', '{safe_file}', TRUE)"
        )

    insert_sql = f"""
        INSERT INTO {_DATABASE}.TRUSTED.FORECAST_VALIDATED (
            ROW_ID, SUPPLIER_ID, SUPPLIER_NAME, BRANCH,
            MATERIAL_CODE, MATERIAL_DESCRIPTION, FORECAST_PERIOD, FORECAST_QUANTITY,
            UPLOAD_ID, UPLOAD_VERSION, UPLOADED_AT, SOURCE_FILE_NAME, IS_ACTIVE
        ) VALUES
        {', '.join(value_rows)}
    """

    try:
        session.sql(insert_sql).collect()
    except Exception as exc:
        _upload_logger.error(
            "persist_validated_forecast: INSERT falhou.\n"
            "  upload_id: %s\n"
            "  linhas_tentadas: %d\n"
            "  erro: %s\n"
            "  tipo: %s",
            upload_id, len(staging_df), exc, type(exc).__name__,
        )
        return 0

    _upload_logger.info(
        "persist_validated_forecast: sucesso — %d linhas inseridas para upload_id=%s",
        len(staging_df), upload_id,
    )
    return len(staging_df)


def _to_date_str(val: str) -> str:
    """
    Converte string de período para formato DATE (YYYY-MM-DD).
    Aceita: 'YYYY-MM-DD', 'YYYY-MM', 'DD/MM/YYYY'.
    Fallback: retorna '1900-01-01' se não conseguir parsear.
    """
    import pandas as pd
    val = val.strip()
    if not val or val == "—":
        return "1900-01-01"

    # Já no formato YYYY-MM-DD
    if len(val) == 10 and val[4] == "-" and val[7] == "-":
        return val

    # Formato YYYY-MM → adiciona dia 01
    if len(val) == 7 and val[4] == "-":
        return f"{val}-01"

    # Tentar parse genérico
    try:
        ts = pd.to_datetime(val, dayfirst=True, errors="coerce")
        if not pd.isna(ts):
            return ts.strftime("%Y-%m-%d")
    except Exception:
        pass

    return "1900-01-01"


def _to_numeric(val) -> str:
    """Converte valor para string numérica segura para SQL."""
    import math
    if val is None:
        return "0"
    try:
        n = float(val)
        if math.isnan(n):
            return "0"
        return str(n)
    except (ValueError, TypeError):
        return "0"
