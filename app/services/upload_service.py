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
    report_type:  str = "Forecast DB"


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
        report_type=  d.get("report_type", "Forecast DB"),
    )


# ---------------------------------------------------------------------------
# Detalhe extra de UP-002 (timeline + validações — dados específicos da tela)
# ---------------------------------------------------------------------------

_UPLOAD_DETAIL_EXTRA: dict[str, dict] = {
    "UP-002": {
        "report_type":  "Forecast DB",
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

    Parâmetros:
        supplier_id  — ID do fornecedor (vem do session_state)
        include_mock — Se True (padrão), mescla uploads da sessão com dados mock.
                       Ignorado quando DEMO_MODE=False: nesse caso apenas dados
                       de sessão são retornados independente do valor do parâmetro.
    """
    from utils.constants import DEMO_MODE
    from utils.session_state import get_session_uploads, get_cancellation

    # Uploads da sessão (mais recentes primeiro — já têm status mutado in-place)
    session_records = [_dict_to_record(d) for d in get_session_uploads(supplier_id)]

    # DEMO_MODE=False → nunca misturar dados mock, independente de include_mock
    if not include_mock or not DEMO_MODE:
        return session_records

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

    Parâmetros:
        period — período de referência no formato "YYYY-MM".
                 Se None (padrão), usa o período da janela aberta atualmente.

    Prioridade de fontes (garante consistência com Forecasts Validados):
    1. session_validated_forecasts (is_active=True) → status "valid"
       Mesma fonte de Forecasts Validados. Usa forecast_period do arquivo,
       normalizado por to_period_ym(). Evita dependência do campo "period"
       em session_uploads, que pode ser "—" por problemas de extração.
    2. session_uploads com status "invalid" → status "invalid"
       Quando não há forecast válido ativo mas há upload inválido no período.
    3. Sem dados → status "pending"

    Retorno: list[dict] com chaves:
        name, code, period, status, last, version, errors, upload_id
    """
    from services.mock_data_service import get_current_open_window
    from utils.dates import to_period_ym
    from utils.session_state import get_session_validated_forecasts

    if period is None:
        window = get_current_open_window()
        period = window["period"] if window else None

    current_period = period

    # --- Fonte primária: forecasts válidos ativos (mesma fonte de Forecasts Validados) ---
    valid_forecasts = get_session_validated_forecasts()  # já filtra is_active=True

    # --- Fonte secundária: uploads inválidos para status "invalid" ---
    all_ups = get_all_uploads(include_mock=True)

    from services.supplier_service import get_all_suppliers

    rows: list[dict] = []
    for s_rec in get_all_suppliers():
        if s_rec.status == "inactive":
            continue  # fornecedores inativos não participam da coleta

        code_upper = s_rec.code.upper()

        # ── 1. Verificar forecasts válidos para este fornecedor no período ──────
        # Compara supplier_id (= código, ex: "SUP001") e normaliza forecast_period
        # para "YYYY-MM" antes de comparar com current_period.
        sup_forecasts = [
            f for f in valid_forecasts
            if str(f.get("supplier_id", "")).upper() == code_upper
            and (
                current_period is None
                or to_period_ym(str(f.get("forecast_period", ""))) == current_period
            )
        ]

        if sup_forecasts:
            try:
                latest_f = max(
                    sup_forecasts,
                    key=lambda f: str(f.get("uploaded_at", "")),
                )
            except (ValueError, TypeError):
                latest_f = sup_forecasts[0]

            rows.append({
                "name":      s_rec.name,
                "code":      s_rec.code,
                "period":    current_period or "—",
                "status":    "valid",
                "last":      str(latest_f.get("uploaded_at", "—")),
                "version":   int(latest_f.get("upload_version", 1)),
                "errors":    0,
                "upload_id": latest_f.get("upload_id"),
            })
            continue

        # ── 2. Verificar upload inválido para este fornecedor no período ─────────
        # Upload inválido = pendente no Painel (não conta como "Com Erro" no card).
        # O erro fica disponível no histórico/detalhe via Gestão de Fornecedores.
        sup_invalid = [
            u for u in all_ups
            if u.supplier_id.upper() == code_upper
            and u.status == "invalid"
            and (
                current_period is None
                or to_period_ym(u.period) == current_period
            )
        ]

        if sup_invalid:
            ref = sup_invalid[0]
            rows.append({
                "name":      s_rec.name,
                "code":      s_rec.code,
                "period":    current_period or ref.period,
                "status":    "pending",   # inválido = pendente no Painel Admin
                "last":      ref.sent_at,
                "version":   "—",
                "errors":    "—",
                "upload_id": ref.upload_id,
            })
            continue

        # ── 3. Sem dados no período → Pendente ────────────────────────────────────
        rows.append({
            "name":      s_rec.name,
            "code":      s_rec.code,
            "period":    current_period or "—",
            "status":    "pending",
            "last":      "—",
            "version":   "—",
            "errors":    "—",
            "upload_id": None,
        })

    return rows


def get_canceled_uploads_count(period: str) -> int:
    """
    Conta uploads válidos que foram cancelados no período informado.

    Usa session_validated_forecasts (is_active=False) para identificar
    quais upload_ids cobrem o período — mesmo que o campo 'period' em
    session_uploads esteja em formato diferente de YYYY-MM.

    Retorna o número de upload_ids distintos cancelados no período.
    """
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

    # Localizar upload_ids cancelados com linhas no período (via forecast_period)
    all_forecasts = st.session_state.get("session_validated_forecasts", [])
    matched: set[str] = set()
    for f in all_forecasts:
        uid = f.get("upload_id")
        if uid in canceled_ids and uid not in matched:
            if to_period_ym(str(f.get("forecast_period", ""))) == period:
                matched.add(uid)

    return len(matched)


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


def simulate_cancel(upload_id: str) -> str:
    """
    Simula o cancelamento lógico de um envio.
    Não remove dados. Retorna mensagem informativa.
    Em produção, atualizará o status no Snowflake para 'CANCELLED'.
    """
    return (
        f"Cancelamento lógico simulado para {upload_id}. "
        "Em produção, o registro será marcado como CANCELLED no Snowflake."
    )


def get_upload_detail(upload_id: str) -> Optional[UploadDetail]:
    """
    Retorna o detalhe completo de um upload pelo seu ID.
    Verifica uploads de sessão antes dos dados mock.
    Em produção, consultará a tabela CONTROL.upload_batches no Snowflake.
    """
    from utils.session_state import get_session_upload_by_id
    import streamlit as st

    # --- Uploads registrados na sessão atual ---
    session_rec = get_session_upload_by_id(upload_id)
    if session_rec is not None:
        return UploadDetail(
            upload_id=         session_rec["upload_id"],
            supplier_name=     session_rec.get("supplier_name", "—"),
            supplier_id=       session_rec.get("supplier_id", "—"),
            file_name=         session_rec.get("file_name", "—"),
            report_type=       session_rec.get("report_type", "Forecast DB"),
            period=            session_rec.get("period", "—"),
            version=           session_rec.get("version", 1),
            status=            session_rec.get("status", "—"),
            # uploaded_by: e-mail salvo no momento do upload (e-mail do fornecedor).
            # Não usar st.session_state["user_email"] pois muda conforme quem visualiza.
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

    # --- Dados mock ---
    raw = get_mock_upload_by_id(upload_id)
    if raw is None:
        return None

    extra = _UPLOAD_DETAIL_EXTRA.get(upload_id, {})

    return UploadDetail(
        upload_id=         raw["upload_id"],
        supplier_name=     raw["supplier_name"],
        supplier_id=       raw["supplier_id"],
        file_name=         raw["file_name"],
        report_type=       extra.get("report_type", "Forecast DB"),
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
