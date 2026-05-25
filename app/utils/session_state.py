"""
session_state.py

Gerenciamento centralizado do st.session_state do Streamlit.
Inicializa as chaves necessárias, provê funções de acesso tipado
e evita erros de KeyError entre navegações de página.

Inclui lógica de versionamento local de uploads:
  - Chave versionável: supplier_id + report_type + reference_period
  - Novo upload válido incrementa versão e marca anteriores como REPLACED
  - Uploads inválidos não alteram a versão ativa
  - is_active reflete qual versão é a vigente para a chave
"""

import streamlit as st
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Valores padrão — todas as chaves usadas pelo app
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "logged_in":              False,
    "role":                   None,
    "page":                   "home",
    "user_name":              "",
    "user_email":             "",
    "user_initials":          "",
    "supplier_id":            None,   # preenchido no login; None para admin
    "supplier_email":         None,   # e-mail do fornecedor logado (login futuro)
    "login_mode":             None,   # "supplier" quando em etapa de seleção de e-mail
    # Contexto de navegação
    "selected_upload_id":     None,
    "detail_upload_id":       None,
    "errors_upload_id":       None,
    "selected_supplier_code": None,
    "origin_page":            None,
    # Flags de estado transitório
    "detail_reprocessed":     False,
    # Uploads registrados na sessão (sem banco)
    "session_uploads":        [],
    "session_errors":         {},
    "session_upload_counter": 0,
    "last_processed_file":    None,
    # Estados transitórios da tela de upload (incluídos em _DEFAULTS para que
    # reset_local_data() os limpe e evite estado stale entre sessões)
    "upload_validate_pending":  False,
    "upload_current_file_key":  None,
    # Cancelamentos: cobre uploads mock (imutáveis) e uploads da sessão
    "session_cancellations":  {},   # dict[upload_id → cancellation_metadata]
    # Fornecedores gerenciados localmente
    # Nota: session_new_suppliers é efêmero (em memória).
    # Para limpar fornecedores cadastrados em testes locais, recarregue a página
    # ou reinicie o servidor Streamlit — a sessão será zerada automaticamente.
    "session_suppliers":          {},   # dict[code_upper → {campos sobrescritos}]
    "session_new_suppliers":      [],   # list[dict] — fornecedores criados na sessão
    "suppliers_form_mode":        None, # "add" | "edit" | None
    "suppliers_edit_code":        None, # code do fornecedor sendo editado
    # Linhas normalizadas de uploads válidos (fonte de verdade de Forecasts Validados)
    "session_validated_forecasts": [],  # list[dict] — uma linha por registro do arquivo
}

# ---------------------------------------------------------------------------
# Status possíveis de um upload (canônico lowercase — compatível com badges)
# ---------------------------------------------------------------------------
STATUS_VALID     = "valid"
STATUS_INVALID   = "invalid"
STATUS_REPLACED  = "replaced"
STATUS_CANCELLED = "canceled"   # mantém "canceled" (sem double l) para compat. badges


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

def init_state() -> None:
    """
    Garante que todas as chaves de session_state existam com valores padrão.
    Deve ser chamado no início de main() em streamlit_app.py.
    """
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = (
                list(default)  if isinstance(default, list)  else
                dict(default)  if isinstance(default, dict)  else
                default
            )


# ---------------------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------------------

def navigate_to(
    page: str,
    upload_id: str | None = None,
    supplier_code: str | None = None,
    origin: str | None = None,
) -> None:
    """
    Navega para a página indicada, armazenando contexto de navegação.
    O origin_page é salvo automaticamente como a página atual se não
    for informado explicitamente.
    """
    st.session_state.origin_page = origin or st.session_state.get("page", "home")
    st.session_state.page = page

    if upload_id is not None:
        st.session_state.selected_upload_id = upload_id
        st.session_state.detail_upload_id   = upload_id
        st.session_state.errors_upload_id   = upload_id
        st.session_state.detail_reprocessed = False

    if supplier_code is not None:
        st.session_state.selected_supplier_code = supplier_code


def get_origin_page(fallback: str = "home") -> str:
    """Retorna a página de origem armazenada, ou o fallback."""
    return st.session_state.get("origin_page") or fallback


# ---------------------------------------------------------------------------
# Limpeza
# ---------------------------------------------------------------------------

def clear_selection() -> None:
    """
    Limpa os contextos de seleção temporários.
    Não remove os uploads registrados na sessão.
    """
    st.session_state.selected_upload_id     = None
    st.session_state.detail_upload_id       = None
    st.session_state.errors_upload_id       = None
    st.session_state.selected_supplier_code = None
    st.session_state.origin_page            = None
    st.session_state.detail_reprocessed     = False


# ---------------------------------------------------------------------------
# Versionamento — funções internas
# ---------------------------------------------------------------------------

def _version_key(supplier_id: str, report_type: str, period: str) -> str:
    """
    Gera a chave canônica de versionamento.
    Formato: SUPPLIER_ID|report_type|AAAA-MM
    Exemplo: SUP001|Forecast DB|2026-05
    """
    return f"{supplier_id.upper()}|{report_type.strip()}|{period.strip()}"


def _mark_previous_as_replaced(version_key: str) -> None:
    """
    Marca como REPLACED todos os uploads da sessão com a mesma
    version_key e status VALID (is_active = True).
    Uploads INVALID não são afetados.
    """
    for record in st.session_state.get("session_uploads", []):
        if (record.get("version_key") == version_key
                and record.get("status") == STATUS_VALID):
            record["status"]    = STATUS_REPLACED
            record["is_active"] = False


# ---------------------------------------------------------------------------
# Geração de ID sequencial
# ---------------------------------------------------------------------------

def next_upload_id() -> str:
    """
    Gera um upload_id sequencial para uploads da sessão.
    Formato: UP-S01, UP-S02, ... (prefixo S = Session).
    """
    st.session_state.session_upload_counter += 1
    return f"UP-S{st.session_state.session_upload_counter:02d}"


# ---------------------------------------------------------------------------
# Cálculo de versão
# ---------------------------------------------------------------------------

def get_upload_version(
    supplier_id: str,
    report_type: str,
    period: str,
) -> int:
    """
    Calcula a próxima versão para a chave (supplier_id, report_type, period).

    Considera:
    1. Uploads mock do mock_data_service — chaveados por (supplier_id, period),
       já que o mock não armazena report_type.
    2. Uploads da sessão — chaveados pela version_key completa de 3 partes.

    Retorna: max(versões encontradas) + 1, ou 1 se for o primeiro envio.
    """
    from services.mock_data_service import get_mock_uploads
    from utils.constants import DEMO_MODE

    versions: list[int] = []
    vk = _version_key(supplier_id, report_type, period)

    # Versões nos dados mock — apenas quando DEMO_MODE=True.
    # Com DEMO_MODE=False o versionamento parte do zero (apenas sessão local).
    if DEMO_MODE:
        for u in get_mock_uploads(supplier_id=supplier_id):
            if u["period"] == period and isinstance(u.get("version"), int):
                versions.append(u["version"])

    # Versões nos uploads da sessão (chave completa)
    for u in st.session_state.get("session_uploads", []):
        if u.get("version_key") == vk and isinstance(u.get("version"), int):
            versions.append(u["version"])

    return max(versions) + 1 if versions else 1


# ---------------------------------------------------------------------------
# Registro de uploads na sessão
# ---------------------------------------------------------------------------

def register_upload(
    file_name:    str,
    supplier_id:  str,
    supplier_name: str,
    period:       str,
    status:       str,
    valid_rows:   int,
    invalid_rows: int,
    report_type:  str = "Forecast DB",
    errors:       Optional[list[dict]] = None,
    uploaded_by:  str = "",
) -> str:
    """
    Registra um novo upload no session_state e retorna o upload_id gerado.

    Regra de versionamento:
    - Chave: supplier_id + report_type + reference_period
    - Versão = max(versões anteriores para a chave) + 1
    - Novo upload VALID → marca versões anteriores válidas como REPLACED (is_active=False)
    - Novo upload INVALID → não altera versões anteriores; is_active=False
    - Status VALID é o único que ativa is_active=True

    Parâmetros:
        file_name     — nome do arquivo original
        supplier_id   — ID do fornecedor logado (vem do session_state)
        supplier_name — nome do fornecedor logado (vem do session_state)
        period        — período de referência AAAA-MM
        status        — "valid" | "invalid"
        valid_rows    — linhas sem erro
        invalid_rows  — linhas com erro (ou total de erros)
        report_type   — tipo de relatório (ex: "Forecast DB")
        errors        — lista de dicts de erros (snake_case) — opcional
        uploaded_by   — e-mail do fornecedor que realizou o upload (não quem visualiza)

    Retorna:
        upload_id gerado (ex: "UP-S01")
    """
    upload_id = next_upload_id()
    vk        = _version_key(supplier_id, report_type, period)
    version   = get_upload_version(supplier_id, report_type, period)
    sent_at   = datetime.now().strftime("%d/%m/%Y %H:%M")
    is_valid  = (status == STATUS_VALID)

    # Uploads VALID substituem versões anteriores válidas da mesma chave
    if is_valid:
        _mark_previous_as_replaced(vk)

    record: dict = {
        "upload_id":     upload_id,
        "supplier_id":   supplier_id.upper(),
        "supplier_name": supplier_name,
        "file_name":     file_name,
        "period":        period,
        "report_type":   report_type,
        "version":       version,
        "version_key":   vk,
        "status":        status,          # lowercase — compatível com badges
        "is_active":     is_valid,        # True apenas para o upload VALID vigente
        "sent_at":       sent_at,
        "valid_rows":    valid_rows,
        "invalid_rows":  invalid_rows,
        "uploaded_by":   uploaded_by,     # e-mail do fornecedor que fez o upload
    }

    # Insere no início (mais recente primeiro)
    st.session_state.session_uploads.insert(0, record)

    # Armazena erros para consulta na tela supplier_errors
    if errors:
        st.session_state.session_errors[upload_id] = errors

    return upload_id


# ---------------------------------------------------------------------------
# Leitura de uploads da sessão
# ---------------------------------------------------------------------------

def get_session_uploads(supplier_id: str) -> list[dict]:
    """
    Retorna uploads da sessão para o supplier_id informado.
    Ordenados por inserção (mais recente primeiro).
    """
    sid = supplier_id.upper().strip()
    return [
        u for u in st.session_state.get("session_uploads", [])
        if u.get("supplier_id", "").upper() == sid
    ]


def get_active_version(
    supplier_id: str,
    report_type: str,
    period: str,
) -> Optional[dict]:
    """
    Retorna o upload ativo (is_active=True) para a chave informada, ou None.
    Útil para confirmar qual versão está vigente antes de um novo envio.
    """
    vk = _version_key(supplier_id, report_type, period)
    for u in st.session_state.get("session_uploads", []):
        if u.get("version_key") == vk and u.get("is_active"):
            return u
    return None


def get_session_errors(upload_id: str) -> Optional[list[dict]]:
    """
    Retorna a lista de erros da sessão para o upload_id informado, ou None.
    """
    return st.session_state.get("session_errors", {}).get(upload_id)


def get_session_upload_by_id(upload_id: str) -> Optional[dict]:
    """
    Retorna o dict de upload de sessão para o upload_id informado, ou None.
    Não filtra por fornecedor — útil para lookup direto por ID.
    """
    for u in st.session_state.get("session_uploads", []):
        if u.get("upload_id") == upload_id:
            return u
    return None


def get_all_session_uploads() -> list[dict]:
    """
    Retorna todos os uploads da sessão, de todos os fornecedores.
    Usado pela visão admin para ter visibilidade completa da sessão.
    """
    return list(st.session_state.get("session_uploads", []))


# ---------------------------------------------------------------------------
# Cancelamento lógico de uploads
# ---------------------------------------------------------------------------

def cancel_upload(
    upload_id:     str,
    cancelled_by:  str,
    cancel_reason: str = "",
) -> bool:
    """
    Cancela logicamente um upload sem excluir nenhum registro.

    Regras:
    - status  → "canceled"  (compatível com badges existentes)
    - is_active → False      (remove da versão ativa)
    - Registra cancelled_at, cancelled_by, cancel_reason

    Para uploads da sessão: muta o dict diretamente.
    Para uploads mock (imutáveis): armazena override em session_cancellations.

    Parâmetros:
        upload_id     — ID do upload a cancelar
        cancelled_by  — e-mail ou nome do usuário que cancelou
        cancel_reason — motivo do cancelamento (opcional, string livre)

    Retorna True se o cancelamento foi registrado com sucesso.
    """
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")

    cancellation_data = {
        "status":        STATUS_CANCELLED,
        "is_active":     False,
        "cancelled_at":  ts,
        "cancelled_by":  cancelled_by,
        "cancel_reason": cancel_reason.strip(),
    }

    # Uploads da sessão — mutação direta
    for record in st.session_state.get("session_uploads", []):
        if record.get("upload_id") == upload_id:
            record.update(cancellation_data)
            # Desativar também as linhas em session_validated_forecasts,
            # para que o forecast cancelado deixe de aparecer em Forecasts Validados
            # e o Painel Admin reflita o status correto (fornecedor volta a Pendente).
            deactivate_validated_forecast(upload_id)
            return True

    # Upload mock (não encontrado na sessão) — armazena override
    if "session_cancellations" not in st.session_state:
        st.session_state.session_cancellations = {}

    st.session_state.session_cancellations[upload_id] = cancellation_data
    return True


def get_cancellation(upload_id: str) -> Optional[dict]:
    """
    Retorna os dados de cancelamento para o upload_id, ou None se não cancelado.
    Usado por upload_service.get_supplier_uploads() para aplicar overrides em mock data.
    """
    return st.session_state.get("session_cancellations", {}).get(upload_id)


# ---------------------------------------------------------------------------
# Reset de dados locais
# ---------------------------------------------------------------------------

def reset_local_data() -> None:
    """
    Limpa todos os dados locais de sessão para teste do zero.

    Após reset:
    - Gestão de Fornecedores fica vazia (sem fornecedores da sessão).
    - Forecasts Validados fica vazio.
    - Login de fornecedor é bloqueado (nenhum e-mail cadastrado).
    - Cards zerados.

    Não afeta configurações do app (DEMO_MODE, etc.).
    Não exclui dados mock — apenas limpa o estado da sessão atual.
    """
    keys_to_reset = [
        # Autenticação
        "logged_in", "role", "page",
        "user_name", "user_email", "user_initials",
        "supplier_id", "supplier_email", "login_mode",
        # Uploads e erros
        "session_uploads", "session_errors",
        "session_upload_counter", "last_processed_file",
        "session_cancellations",
        # Estados transitórios da tela de upload
        "upload_validate_pending", "upload_current_file_key",
        # Fornecedores locais
        "session_new_suppliers", "session_suppliers",
        "suppliers_form_mode", "suppliers_edit_code",
        # Seleções de navegação
        "selected_upload_id", "detail_upload_id",
        "errors_upload_id", "selected_supplier_code",
        "origin_page", "detail_reprocessed",
        # Flags de UI
        "supplier_show_detail", "suppliers_just_saved", "supplier_status_msg",
        # Linhas normalizadas
        "session_validated_forecasts",
    ]
    for key in keys_to_reset:
        if key in _DEFAULTS:
            default = _DEFAULTS[key]
            st.session_state[key] = (
                list(default)  if isinstance(default, list)  else
                dict(default)  if isinstance(default, dict)  else
                default
            )
        elif key in st.session_state:
            del st.session_state[key]


# ---------------------------------------------------------------------------
# Linhas normalizadas de forecasts validados
# ---------------------------------------------------------------------------

def register_validated_forecast(upload_id: str, staging_df) -> None:
    """
    Persiste as linhas normalizadas de um upload válido em session_validated_forecasts.

    - Marca is_active=False nas linhas de outros uploads da mesma
      (supplier_id, forecast_period) — equivalente ao versionamento de uploads.
    - Insere as novas linhas com is_active=True.

    Parâmetros:
        upload_id  — ID do upload já registrado (ex: "UP-S01")
        staging_df — pandas DataFrame com colunas do esquema alvo
    """
    if staging_df is None or len(staging_df) == 0:
        return

    rows = staging_df.to_dict("records")
    if not rows:
        return

    import math

    # Chaves (supplier_id, forecast_period) que este upload cobre
    new_keys: set[tuple] = set()
    for r in rows:
        sid = str(r.get("supplier_id", "")).upper()
        per = str(r.get("forecast_period", ""))
        if sid and per:
            new_keys.add((sid, per))

    # Desativar linhas anteriores das mesmas chaves
    existing: list[dict] = st.session_state.get("session_validated_forecasts", [])
    for row in existing:
        sid = str(row.get("supplier_id", "")).upper()
        per = str(row.get("forecast_period", ""))
        if (sid, per) in new_keys:
            row["is_active"] = False

    # Converter campos pandas → Python nativo para serialização
    clean_rows: list[dict] = []
    for r in rows:
        clean: dict = {}
        for k, v in r.items():
            if hasattr(v, "item"):          # numpy scalar
                v = v.item()
            if isinstance(v, float) and math.isnan(v):
                v = None
            clean[k] = v
        clean["upload_id"] = upload_id
        clean["is_active"] = True
        clean_rows.append(clean)

    st.session_state.session_validated_forecasts.extend(clean_rows)


def get_session_validated_forecasts() -> list[dict]:
    """
    Retorna todas as linhas ativas (is_active=True) de forecasts validados da sessão.
    Filtro por is_active garante que versões substituídas não apareçam.
    """
    return [
        r for r in st.session_state.get("session_validated_forecasts", [])
        if r.get("is_active", True)
    ]


def deactivate_validated_forecast(upload_id: str) -> None:
    """
    Marca todas as linhas do upload_id como is_active=False.
    Chamado quando um upload é cancelado.
    """
    for row in st.session_state.get("session_validated_forecasts", []):
        if row.get("upload_id") == upload_id:
            row["is_active"] = False


# ---------------------------------------------------------------------------
# Gerenciamento local de fornecedores
# ---------------------------------------------------------------------------

def get_session_supplier(code: str) -> Optional[dict]:
    """
    Retorna o dict de override de sessão para o código informado, ou None.
    Usado por supplier_service para aplicar alterações locais sobre o mock.
    """
    return st.session_state.get("session_suppliers", {}).get(code.upper())


def set_session_supplier(code: str, overrides: dict) -> None:
    """
    Aplica overrides de sessão para o fornecedor com o código informado.
    Se já existir um override, faz merge (não substitui campos não informados).
    Persiste o código original no override para facilitar merges futuros.
    """
    key     = code.upper()
    current = st.session_state.setdefault("session_suppliers", {})
    current[key] = {**(current.get(key) or {}), **overrides, "code": code}


def add_new_session_supplier(supplier_dict: dict) -> None:
    """
    Adiciona um novo fornecedor criado localmente (não existente no mock).
    O dict deve conter todos os campos de um fornecedor completo.
    """
    st.session_state.setdefault("session_new_suppliers", []).append(supplier_dict)


def get_new_session_suppliers() -> list[dict]:
    """Retorna a lista de fornecedores criados na sessão atual."""
    return list(st.session_state.get("session_new_suppliers", []))


def get_all_session_supplier_codes() -> set[str]:
    """Retorna conjunto de códigos de todos os fornecedores conhecidos (mock + novos)."""
    new_codes = {d["code"].upper() for d in get_new_session_suppliers()}
    return new_codes
