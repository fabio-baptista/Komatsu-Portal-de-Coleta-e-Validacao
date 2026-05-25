"""
supplier_service.py

Serviço de dados de fornecedores.
Responsável por retornar a lista de fornecedores, seus dados cadastrais
e o status de envio por ciclo.

Camadas de dados (prioridade decrescente):
1. Fornecedores criados na sessão  (session_new_suppliers)
2. Overrides de sessão sobre mock  (session_suppliers)
3. Mock base                       (mock_data_service)

NOTA: Em produção, substituir pela consulta ao cadastro corporativo.
"""

from dataclasses import dataclass, field

from services.mock_data_service import get_mock_suppliers, get_mock_supplier_by_code


# ---------------------------------------------------------------------------
# Tipo de dados
# ---------------------------------------------------------------------------

@dataclass
class SupplierRecord:
    """
    Representa um fornecedor cadastrado no portal.

    Nota de produção:
    - O campo 'email' será usado como identificador de login futuro.
    - Fornecedores NÃO devem ser excluídos fisicamente, pois podem ter histórico
      de uploads, versões, erros e forecasts. Para remover da operação, usar
      status Inativo.
    - Em produção, persistir em CONTROL.suppliers ou tabela equivalente.
    """
    code:                str
    name:                str
    status:              str   # "active" | "inactive"
    email:               str   # identificador de login futuro — único e em minúsculas
    forecast_participant: bool  # derivado de status: ativo = True, inativo = False
    last_upload:         str   # DD/MM/AAAA ou "—"
    period_status:       str   # valid | invalid | pending | not_expected
    recent_uploads:      list[dict] = field(default_factory=list)
    users:               list[str]  = field(default_factory=list)


# ---------------------------------------------------------------------------
# Conversão de dict → SupplierRecord
# ---------------------------------------------------------------------------

def _dict_to_record(d: dict) -> SupplierRecord:
    status = d.get("status", "active")
    # Email: campo explícito, ou primeiro elemento de 'users' como fallback para mock
    raw_email = d.get("email", "") or (d["users"][0] if d.get("users") else "")
    email     = raw_email.strip().lower()
    return SupplierRecord(
        code=                d["code"],
        name=                d["name"],
        status=              status,
        email=               email,
        forecast_participant=(status == "active"),
        last_upload=         d.get("last_upload", "—"),
        period_status=       d.get("period_status", "pending"),
        recent_uploads=      list(d.get("recent_uploads", [])),
        users=               list(d.get("users", [])),
    )


# ---------------------------------------------------------------------------
# Funções de acesso
# ---------------------------------------------------------------------------

def get_all_suppliers() -> list[SupplierRecord]:
    """
    Retorna a lista de fornecedores respeitando o modo configurado em DEMO_MODE.

    DEMO_MODE = False (padrão / teste funcional):
        Retorna apenas os fornecedores cadastrados na sessão atual.
        Estado inicial: lista vazia.

    DEMO_MODE = True (apresentação/demo):
        Retorna fornecedores mockados (com overrides de sessão aplicados)
        + fornecedores novos criados na sessão.
    """
    from utils.constants import DEMO_MODE
    from utils.session_state import get_session_supplier, get_new_session_suppliers

    # Fornecedores criados na sessão — COM overrides aplicados.
    # Isso garante que set_session_supplier() (Inativar/Ativar/Editar)
    # reflita imediatamente, independente do DEMO_MODE.
    session_suppliers: list[SupplierRecord] = []
    for d in get_new_session_suppliers():
        override = get_session_supplier(d["code"]) or {}
        session_suppliers.append(_dict_to_record({**d, **override}))

    if not DEMO_MODE:
        # Modo funcional: apenas fornecedores cadastrados na sessão (com overrides)
        return session_suppliers

    # Modo demonstração: mock (com overrides) + sessão (com overrides)
    result: list[SupplierRecord] = []
    for d in get_mock_suppliers():
        override = get_session_supplier(d["code"]) or {}
        result.append(_dict_to_record({**d, **override}))

    result.extend(session_suppliers)
    return result


def get_supplier_by_code(code: str) -> SupplierRecord | None:
    """
    Retorna um fornecedor pelo código (case-insensitive).
    Aplica overrides de sessão e cobre fornecedores criados localmente.
    Retorna None se não encontrado.
    """
    for s in get_all_suppliers():
        if s.code.upper() == code.upper():
            return s
    return None


def get_next_supplier_code() -> str:
    """
    Retorna o próximo código de fornecedor disponível no formato SUP001, SUP002, …

    Regras:
    - Analisa todos os códigos existentes (mock + overrides + novos da sessão).
    - Considera apenas códigos que seguem o padrão SUP + 3 dígitos.
    - Retorna SUP + (maior_número + 1) com zero-padding de 3 dígitos.
    - Se nenhum código no padrão existir, retorna SUP001.
    - O código gerado é garantidamente único na lista atual.
    """
    import re
    all_codes = [s.code.upper() for s in get_all_suppliers()]
    pattern   = re.compile(r"^SUP(\d{3})$")
    numbers   = [
        int(m.group(1))
        for code in all_codes
        if (m := pattern.match(code))
    ]
    next_num = (max(numbers) + 1) if numbers else 1
    return f"SUP{next_num:03d}"


def get_summary() -> dict:
    """
    Retorna métricas de cadastro de fornecedores para os cards de resumo.

    No MVP local, fornecedores são mantidos em session_state.
    Em produção, este cadastro deverá ser persistido em CONTROL.suppliers
    ou tabela equivalente no Snowflake.
    """
    all_s = get_all_suppliers()
    return {
        "total_active":   sum(1 for s in all_s if s.status == "active"),
        "total_inactive": sum(1 for s in all_s if s.status == "inactive"),
    }
