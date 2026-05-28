"""
mock_data_service.py

Camada centralizada de dados fictícios para o Portal Komatsu MVP.
Consolida todos os dados de demonstração: usuários, fornecedores, uploads,
erros de validação, dados validados (forecast) e janelas de envio.

Regras:
- Retorna tipos primitivos (dicts e listas) para evitar imports circulares.
- Cada serviço converte os dicts para seus próprios dataclasses.
- Todos os IDs, supplier_ids e períodos são consistentes entre as telas.
- Não conecta com Snowflake. Substituir chamadas por queries reais na integração.

Relações:
  SUP001 / Vianmaq        → UP-001 (replaced), UP-002 (valid/ativo), UP-003 (invalid junho), UP-004 (canceled)
  SUP002 / Dist Uberlândia → sem upload Maio/2026 (pending)
  SUP003 / Fornecedor X   → UP-005 (invalid maio)
  SUP004 / Fornecedor Y   → inativo / não esperado
  SUP005 / Mecânica Centro → sem upload Maio/2026 (pending)
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------

_USERS: list[dict] = [
    {
        "profile":       "supplier",
        "name":          "Vianmaq S.A.",
        "email":         "joao.vianmaq@email.com",
        "initials":      "JV",
        "supplier_id":   "SUP001",
        "supplier_name": "Vianmaq",
    },
    {
        "profile":       "admin",
        "name":          "Komatsu Corp",
        "email":         "admin.komatsu@email.com",
        "initials":      "AK",
        "supplier_id":   None,
        "supplier_name": None,
    },
]


# ---------------------------------------------------------------------------
# Janelas de envio
# ---------------------------------------------------------------------------

_SUBMISSION_WINDOWS: list[dict] = [
    {
        "period":       "2026-05",
        "label":        "Maio/2026",
        "open":         True,
        "closes_at":    "05/05/2026",
        "progress_pct": 85,
    },
    {
        "period":       "2026-06",
        "label":        "Junho/2026",
        "open":         False,
        "closes_at":    "—",
        "progress_pct": 0,
    },
]


# ---------------------------------------------------------------------------
# Fornecedores
# ---------------------------------------------------------------------------

_SUPPLIERS: list[dict] = [
    {
        "code":           "SUP001",
        "name":           "Vianmaq",
        "status":         "active",
        "users":          ["joao.vianmaq@email.com", "maria.vianmaq@email.com"],
        "last_upload":    "04/05/2026",
        "period_status":  "valid",
        "recent_uploads": [
            {"period": "2026-05", "type": "Forecast DB", "version": 2, "status": "valid"},
            {"period": "2026-06", "type": "Forecast DB", "version": 1, "status": "invalid"},
        ],
    },
    {
        "code":           "SUP002",
        "name":           "Distribuidor Uberlândia",
        "status":         "active",
        "users":          ["contato@distribuidoruba.com.br"],
        "last_upload":    "—",
        "period_status":  "pending",
        "recent_uploads": [
            {"period": "2026-04", "type": "Forecast DB", "version": 1, "status": "valid"},
        ],
    },
    {
        "code":           "SUP003",
        "name":           "Fornecedor X",
        "status":         "active",
        "users":          ["operacoes@fornecedorx.com"],
        "last_upload":    "04/05/2026",
        "period_status":  "invalid",
        "recent_uploads": [
            {"period": "2026-05", "type": "Forecast DB", "version": 1, "status": "invalid"},
        ],
    },
    {
        "code":           "SUP004",
        "name":           "Fornecedor Y",
        "status":         "inactive",
        "users":          [],
        "last_upload":    "—",
        "period_status":  "not_expected",
        "recent_uploads": [],
    },
    {
        "code":           "SUP005",
        "name":           "Mecânica Centro",
        "status":         "active",
        "users":          ["suprimentos@mecanicacentro.com.br"],
        "last_upload":    "—",
        "period_status":  "pending",
        "recent_uploads": [],
    },
]


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------
# UP-001..UP-004 pertencem a Vianmaq (SUP001).
# UP-005 pertence a Fornecedor X (SUP003) — Maio/2026, inválido, 8 erros.
# ---------------------------------------------------------------------------

_UPLOADS: list[dict] = [
    {
        "upload_id":     "UP-001",
        "supplier_id":   "SUP001",
        "supplier_name": "Vianmaq",
        "file_name":     "forecast_vianmaq_maio.xlsx",
        "period":        "2026-05",
        "version":       1,
        "status":        "replaced",
        "sent_at":       "03/05/2026 10:22",
        "valid_rows":    120,
        "invalid_rows":  0,
    },
    {
        "upload_id":     "UP-002",
        "supplier_id":   "SUP001",
        "supplier_name": "Vianmaq",
        "file_name":     "forecast_vianmaq_maio_v2.xlsx",
        "period":        "2026-05",
        "version":       2,
        "status":        "valid",
        "sent_at":       "04/05/2026 09:10",
        "valid_rows":    124,
        "invalid_rows":  0,
    },
    {
        "upload_id":     "UP-003",
        "supplier_id":   "SUP001",
        "supplier_name": "Vianmaq",
        "file_name":     "forecast_vianmaq_junho.xlsx",
        "period":        "2026-06",
        "version":       1,
        "status":        "invalid",
        "sent_at":       "04/05/2026 14:33",
        "valid_rows":    0,
        "invalid_rows":  8,
    },
    {
        "upload_id":     "UP-004",
        "supplier_id":   "SUP001",
        "supplier_name": "Vianmaq",
        "file_name":     "forecast_vianmaq_abril.xlsx",
        "period":        "2026-04",
        "version":       1,
        "status":        "canceled",
        "sent_at":       "02/04/2026 16:20",
        "valid_rows":    118,
        "invalid_rows":  0,
    },
    {
        "upload_id":     "UP-005",
        "supplier_id":   "SUP003",
        "supplier_name": "Fornecedor X",
        "file_name":     "forecast_fornecedorx_maio.xlsx",
        "period":        "2026-05",
        "version":       1,
        "status":        "invalid",
        "sent_at":       "04/05/2026 14:33",
        "valid_rows":    0,
        "invalid_rows":  8,
    },
]


# ---------------------------------------------------------------------------
# Erros de validação por upload_id
# ---------------------------------------------------------------------------

_VALIDATION_ERRORS: dict[str, list[dict]] = {
    "UP-003": [
        {"linha": 15, "coluna": "material_code",    "valor_informado": "(vazio)",   "erro": "Campo obrigatório", "orientacao_correcao": "Informar código do material"},
        {"linha": 22, "coluna": "forecast_quantity", "valor_informado": "ABC",       "erro": "Tipo inválido",     "orientacao_correcao": "Informar valor numérico"},
        {"linha": 31, "coluna": "forecast_period",   "valor_informado": "32/13/2026","erro": "Data inválida",     "orientacao_correcao": "Informar data válida (DD/MM/AAAA ou AAAA-MM-DD)"},
        {"linha": 44, "coluna": "branch",            "valor_informado": "(vazio)",   "erro": "Campo obrigatório", "orientacao_correcao": "Informar filial/localidade"},
        {"linha": 58, "coluna": "forecast_quantity", "valor_informado": "-10",       "erro": "Valor negativo",    "orientacao_correcao": "Quantidade deve ser maior ou igual a zero"},
        {"linha": 63, "coluna": "material_code",     "valor_informado": "(vazio)",   "erro": "Campo obrigatório", "orientacao_correcao": "Informar código do material"},
        {"linha": 71, "coluna": "forecast_quantity", "valor_informado": "N/A",       "erro": "Tipo inválido",     "orientacao_correcao": "Informar valor numérico"},
        {"linha": 89, "coluna": "forecast_period",   "valor_informado": "(vazio)",   "erro": "Campo obrigatório", "orientacao_correcao": "Informar a data de recebimento"},
    ],
    "UP-005": [
        {"linha": 8,  "coluna": "material_code",    "valor_informado": "(vazio)",    "erro": "Campo obrigatório", "orientacao_correcao": "Informar código do material"},
        {"linha": 14, "coluna": "forecast_quantity", "valor_informado": "—",          "erro": "Tipo inválido",     "orientacao_correcao": "Informar valor numérico"},
        {"linha": 19, "coluna": "forecast_period",   "valor_informado": "00/00/0000", "erro": "Data inválida",     "orientacao_correcao": "Informar data válida (DD/MM/AAAA ou AAAA-MM-DD)"},
        {"linha": 27, "coluna": "branch",            "valor_informado": "(vazio)",    "erro": "Campo obrigatório", "orientacao_correcao": "Informar filial/localidade"},
        {"linha": 35, "coluna": "forecast_quantity", "valor_informado": "-5",         "erro": "Valor negativo",    "orientacao_correcao": "Quantidade deve ser maior ou igual a zero"},
        {"linha": 42, "coluna": "material_code",     "valor_informado": "???",        "erro": "Campo obrigatório", "orientacao_correcao": "Informar código do material"},
        {"linha": 50, "coluna": "forecast_quantity", "valor_informado": "N/D",        "erro": "Tipo inválido",     "orientacao_correcao": "Informar valor numérico"},
        {"linha": 67, "coluna": "forecast_period",   "valor_informado": "(vazio)",    "erro": "Campo obrigatório", "orientacao_correcao": "Informar a data de recebimento"},
    ],
}


# ---------------------------------------------------------------------------
# Forecast validado — simulação de TRUSTED.forecast_validated
# ---------------------------------------------------------------------------

_VALIDATED_FORECAST: list[dict] = [
    {
        "supplier":     "Vianmaq",
        "branch":       "Marialva",
        "material_code":"600-319-3610",
        "description":  "Filtro Hidráulico",
        "period":       "2026-05",
        "qty":          57,
        "version":      2,
        "processed_at": "04/05/2026",
        "source_file":  "forecast_vianmaq_maio_v2.xlsx",
    },
    {
        "supplier":     "Vianmaq",
        "branch":       "Marialva",
        "material_code":"600-319-3750",
        "description":  "Elemento Filtrante",
        "period":       "2026-05",
        "qty":          42,
        "version":      2,
        "processed_at": "04/05/2026",
        "source_file":  "forecast_vianmaq_maio_v2.xlsx",
    },
    {
        "supplier":     "Vianmaq",
        "branch":       "Marialva",
        "material_code":"20Y-60-31211",
        "description":  "Filtro de Ar",
        "period":       "2026-05",
        "qty":          31,
        "version":      2,
        "processed_at": "04/05/2026",
        "source_file":  "forecast_vianmaq_maio_v2.xlsx",
    },
    {
        "supplier":     "Distribuidor Uberlândia",
        "branch":       "Uberlândia",
        "material_code":"07000-37760",
        "description":  "Filtro de Combustível",
        "period":       "2026-04",
        "qty":          24,
        "version":      1,
        "processed_at": "05/04/2026",
        "source_file":  "dist_uberlandia_abril.xlsx",
    },
    {
        "supplier":     "Distribuidor Uberlândia",
        "branch":       "Uberlândia",
        "material_code":"600-411-1152",
        "description":  "Filtro de Óleo",
        "period":       "2026-04",
        "qty":          18,
        "version":      1,
        "processed_at": "05/04/2026",
        "source_file":  "dist_uberlandia_abril.xlsx",
    },
]


# ---------------------------------------------------------------------------
# Tabela admin consolidada (supplier × período — pré-calculada para exibição)
# ---------------------------------------------------------------------------
# Derivada de _SUPPLIERS + _UPLOADS. Mantida aqui para evitar lógica de join
# nas camadas de componente e exibição.

_ADMIN_TABLE_ROWS: list[dict] = [
    {
        "name":    "Vianmaq",
        "period":  "2026-05",
        "status":  "valid",
        "last":    "04/05/2026 09:10",
        "version": 2,
        "errors":  0,
        "upload_id": "UP-002",
    },
    {
        "name":    "Distribuidor Uberlândia",
        "period":  "2026-05",
        "status":  "pending",
        "last":    "—",
        "version": "—",
        "errors":  "—",
        "upload_id": None,
    },
    {
        "name":    "Fornecedor X",
        "period":  "2026-05",
        "status":  "invalid",
        "last":    "04/05/2026 14:33",
        "version": 1,
        "errors":  8,
        "upload_id": "UP-005",
    },
    {
        "name":    "Fornecedor Y",
        "period":  "2026-05",
        "status":  "not_expected",
        "last":    "—",
        "version": "—",
        "errors":  "—",
        "upload_id": None,
    },
    {
        "name":    "Mecânica Centro",
        "period":  "2026-05",
        "status":  "pending",
        "last":    "—",
        "version": "—",
        "errors":  "—",
        "upload_id": None,
    },
]


# ---------------------------------------------------------------------------
# Funções de acesso
# ---------------------------------------------------------------------------

def get_mock_users() -> list[dict]:
    """Retorna todos os usuários mockados do portal."""
    return list(_USERS)


def get_current_mock_user(profile: str) -> dict:
    """
    Retorna os dados do usuário mockado para o perfil informado.
    profile: "supplier" | "admin"
    Retorna o primeiro usuário da lista se o perfil não for encontrado.
    """
    for u in _USERS:
        if u["profile"] == profile:
            return u
    return _USERS[0]


def get_mock_submission_windows() -> list[dict]:
    """Retorna as janelas de envio mockadas."""
    return list(_SUBMISSION_WINDOWS)


def get_current_open_window() -> Optional[dict]:
    """Retorna a janela aberta. Usa CONTROL.SUBMISSION_WINDOWS se disponivel, senao mock."""
    try:
        from services.snowflake_service import execute_query, is_running_in_snowflake
        if is_running_in_snowflake():
            df = execute_query(
                "SELECT * FROM KBI_DATA_JOURNEY_DEV_DB.CONTROL.SUBMISSION_WINDOWS WHERE IS_OPEN = TRUE LIMIT 1"
            )
            if df is not None and not df.empty:
                row = df.iloc[0].to_dict()
                return {
                    "window_id":  str(row["WINDOW_ID"]),
                    "period":     str(row["REFERENCE_PERIOD"]),
                    "label":      f"{str(row['REPORT_TYPE'])} — {str(row['REFERENCE_PERIOD'])}",
                    "start_date": str(row["START_DATE"]),
                    "end_date":   str(row["END_DATE"]),
                    "is_open":    True,
                }
            return None
    except Exception:
        pass
    for w in _SUBMISSION_WINDOWS:
        if w["open"]:
            return w
    return None


def get_mock_suppliers() -> list[dict]:
    """Retorna todos os fornecedores mockados como dicts."""
    return list(_SUPPLIERS)


def get_mock_supplier_by_code(code: str) -> Optional[dict]:
    """Retorna um fornecedor pelo código (case-insensitive), ou None."""
    for s in _SUPPLIERS:
        if s["code"].upper() == code.upper():
            return s
    return None


def get_mock_uploads(supplier_id: Optional[str] = None) -> list[dict]:
    """
    Retorna uploads mockados.
    Se supplier_id informado, filtra pelo fornecedor (case-insensitive).
    """
    if supplier_id:
        sid = supplier_id.upper()
        return [u for u in _UPLOADS if u["supplier_id"].upper() == sid]
    return list(_UPLOADS)


def get_mock_upload_by_id(upload_id: str) -> Optional[dict]:
    """Retorna um upload pelo ID, ou None se não encontrado."""
    for u in _UPLOADS:
        if u["upload_id"] == upload_id:
            return u
    return None


def get_mock_validation_errors(upload_id: Optional[str] = None) -> list[dict]:
    """
    Retorna a lista de erros mockados para o upload informado.
    Se upload_id for None, retorna os erros de UP-003 (fallback padrão).
    Retorna lista vazia se o upload não tiver erros registrados.
    """
    key = upload_id if upload_id else "UP-003"
    return list(_VALIDATION_ERRORS.get(key, []))


def get_mock_validated_forecast() -> list[dict]:
    """
    Retorna os registros mockados da camada TRUSTED.forecast_validated.
    Com DEMO_MODE=False retorna lista vazia — sem dados demo em modo funcional.
    """
    from utils.constants import DEMO_MODE
    if not DEMO_MODE:
        return []
    return list(_VALIDATED_FORECAST)


def get_admin_table_rows() -> list[dict]:
    """
    Retorna as linhas da tabela admin consolidada (fornecedor × período).
    Inclui upload_id para navegação às telas de detalhe e erros.
    """
    return list(_ADMIN_TABLE_ROWS)
