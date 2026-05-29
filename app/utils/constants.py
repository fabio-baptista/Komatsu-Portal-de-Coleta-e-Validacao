"""
constants.py

Constantes globais da aplicação.
Centraliza valores fixos como nomes de colunas esperadas no template,
status possíveis de envio, perfis de usuário, cores da identidade visual
e parâmetros de configuração do portal.
"""

import os

# ---------------------------------------------------------------------------
# Ambiente de execução
# ---------------------------------------------------------------------------
# APP_ENV controla funcionalidades exclusivas de desenvolvimento/teste.
# Valores: "dev" | "test" | "local" | "production"
# Default: "dev" (desenvolvimento local é o cenário mais comum).
# Em produção, definir APP_ENV=production para ocultar ferramentas de teste.
APP_ENV: str = os.environ.get("APP_ENV", "dev")

# ---------------------------------------------------------------------------
# Mapeamento de colunas: nome canônico → variantes aceitas no arquivo enviado
# ---------------------------------------------------------------------------
COLUMN_ALIASES: dict[str, list[str]] = {
    "material": [
        "Material", "MATERIAL", "material_code", "Código Material",
        "codigo_material", "CODIGO_MATERIAL",
    ],
    "quantidade": [
        "Quantidade", "Qtd", "QTD", "QUANTIDADE", "forecast_quantity",
        "Qtde", "QTDE", "qty", "QTY",
    ],
    "data_recebimento": [
        "Data_recebimento", "Data Recebimento", "DATA_RECEBIMENTO",
        "forecast_period", "Data", "DATA", "Periodo", "PERIODO", "Período",
    ],
    "cidade_filial": [
        "Cidade_Filial", "Filial", "FILIAL", "branch", "CIDADE_FILIAL",
        "Cidade Filial", "cidade_filial",
    ],
}

# Colunas obrigatórias (nomes canônicos)
REQUIRED_COLUMNS: list[str] = list(COLUMN_ALIASES.keys())

# Extensões de arquivo aceitas
ALLOWED_EXTENSIONS: list[str] = [".xlsx", ".csv"]

# Limite de tamanho de arquivo (MB) — informativo, validação real é pelo Streamlit
MAX_FILE_SIZE_MB: int = 50

# Status possíveis de um envio
UPLOAD_STATUS = {
    "valid":     "Válido/Ativo",
    "invalid":   "Inválido",
    "replaced":  "Substituído",
    "canceled":  "Cancelado",
    "processed": "Processado",
    "pending":   "Pendente",
}

# Perfis de usuário
USER_ROLES = {
    "supplier": "Fornecedor",
    "admin":    "Administrativo",
}

# ---------------------------------------------------------------------------
# Modo de demonstração — Gestão de Fornecedores
# ---------------------------------------------------------------------------
# DEMO_MODE = True  → carrega fornecedores mockados + fornecedores da sessão
# DEMO_MODE = False → usa APENAS fornecedores cadastrados na sessão atual
#
# Para teste funcional (comportamento real), manter False.
# Para apresentação/demo com dados pré-carregados, trocar para True.
DEMO_MODE: bool = False

# ---------------------------------------------------------------------------
# Tipo de relatório padrão
# ---------------------------------------------------------------------------
# Valor usado como REPORT_TYPE em CONTROL.UPLOAD_BATCHES e SUBMISSION_WINDOWS.
# Centralizado aqui para facilitar futura evolução multi-report.
DEFAULT_REPORT_TYPE: str = "Forecast DB"


# ---------------------------------------------------------------------------
# Registry de tipos de relatório
# ---------------------------------------------------------------------------
# Cada tipo de relatório define: template, colunas, tabela destino e flag de habilitação.
# Funções (validator, normalizer, persist) são resolvidas em get_report_type_config()
# via lazy import para evitar dependência circular.
#
# Para adicionar um novo tipo no futuro:
#   1. Criar entrada no REPORT_TYPE_REGISTRY com enabled=False até implementar.
#   2. Criar validator, normalizer e persist function no respectivo service.
#   3. Criar template na pasta templates/.
#   4. Criar tabela TRUSTED correspondente.
#   5. Alterar get_report_type_config() para incluir os callables.
#   6. Habilitar com enabled=True.
# ---------------------------------------------------------------------------

REPORT_TYPE_REGISTRY: dict[str, dict] = {
    "Forecast DB": {
        "key": "forecast",
        "label": "Forecast DB",
        "template_xlsx": "template_forecast.xlsx",
        "template_csv": "template_forecast.csv",
        "expected_columns": [
            "Data_Envio",
            "Distribuidor_Nome",
            "Cidade_Filial",
            "NFMAT",
            "MATERIAL",
            "Descrição",
            "Ranking_Nacional",
            "Qtd",
            "Data_recebimento",
            "Observacoes",
        ],
        "column_aliases": COLUMN_ALIASES,
        "required_columns": REQUIRED_COLUMNS,
        "trusted_table": "TRUSTED.FORECAST_VALIDATED",
        "enabled": True,
    },
    # -------------------------------------------------------------------------
    # Evolução futura — tipos previstos mas NÃO implementados:
    # -------------------------------------------------------------------------
    # "Vendas": {
    #     "key": "sales",
    #     "label": "Vendas",
    #     "template_xlsx": "template_vendas.xlsx",
    #     "template_csv": "template_vendas.csv",
    #     "expected_columns": [...],
    #     "column_aliases": {...},
    #     "required_columns": [...],
    #     "trusted_table": "TRUSTED.SALES_VALIDATED",
    #     "enabled": False,
    # },
    # "Vendas Perdidas": {
    #     "key": "lost_sales",
    #     "label": "Vendas Perdidas",
    #     "trusted_table": "TRUSTED.LOST_SALES_VALIDATED",
    #     "enabled": False,
    # },
    # "Estoque": {
    #     "key": "inventory",
    #     "label": "Estoque",
    #     "trusted_table": "TRUSTED.INVENTORY_VALIDATED",
    #     "enabled": False,
    # },
}


def get_report_type_config(report_type: str = DEFAULT_REPORT_TYPE) -> dict:
    """
    Retorna a configuração completa para um tipo de relatório, incluindo
    referências a funções (validator, normalizer, persist) via lazy import.

    Raises:
        ValueError se o tipo não existir ou não estiver habilitado.

    Uso:
        config = get_report_type_config("Forecast DB")
        result = config["validator"](df, supplier_name=name)
        norm   = config["normalizer"](...)
        count  = config["persist_trusted"](...)
    """
    config = REPORT_TYPE_REGISTRY.get(report_type)
    if config is None:
        raise ValueError(f"Tipo de relatório '{report_type}' não registrado.")
    if not config.get("enabled"):
        raise ValueError(f"Tipo de relatório '{report_type}' não está habilitado.")

    # Lazy imports para evitar dependência circular
    from services.validation_service import validate_forecast
    from services.forecast_service import normalize_forecast
    from services.upload_service import persist_validated_forecast

    return {
        **config,
        "validator": validate_forecast,
        "normalizer": normalize_forecast,
        "persist_trusted": persist_validated_forecast,
    }
