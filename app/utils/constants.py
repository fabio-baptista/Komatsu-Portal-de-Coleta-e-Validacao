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
        "Material", "MATERIAL", "material_code", "Código", "Codigo",
        "Código Material", "Codigo Material", "codigo_material", "CODIGO_MATERIAL",
    ],
    "quantidade": [
        "Quantidade", "Qtd", "QTD", "QUANTIDADE", "forecast_quantity",
        "Qtde", "QTDE", "qty", "QTY", "Quant.",
    ],
    "data_recebimento": [
        "Data Recebimento", "Data_recebimento", "DATA_RECEBIMENTO",
        "Data de Recebimento", "Dt Recebimento",
        "forecast_period", "Data", "DATA", "Periodo", "PERIODO", "Período",
    ],
    "cidade_filial": [
        "Filial", "Cidade_Filial", "FILIAL", "branch", "CIDADE_FILIAL",
        "Cidade Filial", "cidade_filial", "Branch",
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
    "supplier": "Distribuidor",
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

# ---------------------------------------------------------------------------
# Aliases e colunas por tipo de relatório
# ---------------------------------------------------------------------------

STOCK_COLUMN_ALIASES: dict[str, list[str]] = {
    "material_code": [
        "Código", "Codigo", "CODIGO", "Material", "MATERIAL", "NFMAT", "Item",
        "material_code",
    ],
    "material_description": [
        "Descrição", "Descricao", "DESCRICAO", "Descrição Material", "Desc",
        "material_description",
    ],
    "stock_quantity": [
        "Quantidade", "Qtd", "QTD", "Qtde", "QTDE", "Quant.",
        "stock_quantity", "qty", "QTY", "QUANTIDADE",
    ],
    "unit_cost": [
        "Custo Unitário", "Custo Unitario", "Custo Unit", "Custo_Unit",
        "Valor Unitário", "Valor Unitario", "CUSTO UNIT",
        "unit_cost",
    ],
    "total_cost": [
        "Custo Total", "Valor Total", "Total", "CUSTO TOTAL",
        "Custo_Total", "total_cost",
    ],
    "purchase_date": [
        "Data Compra", "Data da Compra", "Dt Compra", "Data_Compra",
        "DATA COMPRA", "purchase_date",
    ],
    "last_sale_date": [
        "Data Última Venda", "Data Ultima Venda", "Data da Última Venda",
        "Data da Ultima Venda", "Dt Última Venda", "Dt Ultima Venda",
        "Data_Ultima_Venda", "last_sale_date",
    ],
    "branch": [
        "Filial", "FILIAL", "Cidade Filial", "Cidade_Filial",
        "Branch", "branch", "cidade_filial",
    ],
    "supplier_name": [
        "DB", "Distribuidor", "Distribuidor_Nome", "DISTRIBUIDOR",
    ],
    "year": [
        "ANO", "Ano", "year",
    ],
    "month": [
        "MÊS", "MES", "Mês", "Mes", "month",
    ],
    "invoice_number": [
        "N.F. Compra", "NF Compra", "Nota Fiscal", "Nota Fiscal Compra",
        "NF", "NF_Compra", "invoice_number",
    ],
}

STOCK_REQUIRED_COLUMNS: list[str] = [
    "material_code",
    "stock_quantity",
    "unit_cost",
    "purchase_date",
    "branch",
]


REPORT_TYPE_REGISTRY: dict[str, dict] = {
    "Estoque": {
        "key": "stock",
        "label": "Estoque",
        "template_xlsx": "template_stock.xlsx",
        "template_csv": "template_stock.csv",
        "expected_columns": [
            "Código",
            "Descrição",
            "Quantidade",
            "Custo Unitário",
            "Custo Total",
            "Data Compra",
            "N.F. Compra",
            "Data Última Venda",
            "Filial",
        ],
        "column_aliases": STOCK_COLUMN_ALIASES,
        "required_columns": STOCK_REQUIRED_COLUMNS,
        "trusted_table": "TRUSTED.STOCK_VALIDATED",
        "enabled": True,
    },
    "Forecast DB": {
        "key": "forecast",
        "label": "Forecast DB",
        "template_xlsx": "template_forecast.xlsx",
        "template_csv": "template_forecast.csv",
        "expected_columns": [
            "Data Envio",
            "Distribuidor",
            "Filial",
            "NFMAT",
            "Material",
            "Descrição",
            "Ranking Nacional",
            "Quantidade",
            "Data Recebimento",
            "Observações",
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
    #     "trusted_table": "TRUSTED.SALES_VALIDATED",
    #     "enabled": False,
    # },
    # "Vendas Perdidas": {
    #     "key": "lost_sales",
    #     "label": "Vendas Perdidas",
    #     "trusted_table": "TRUSTED.LOST_SALES_VALIDATED",
    #     "enabled": False,
    # },
}


def get_enabled_report_types() -> list[str]:
    """Retorna os labels dos report types habilitados."""
    return [k for k, v in REPORT_TYPE_REGISTRY.items() if v.get("enabled")]


def get_report_type_config(report_type: str = DEFAULT_REPORT_TYPE) -> dict:
    """
    Retorna a configuração completa para um tipo de relatório, incluindo
    referências a funções (validator, normalizer, persist) via lazy import.

    Raises:
        ValueError se o tipo não existir ou não estiver habilitado.
    """
    config = REPORT_TYPE_REGISTRY.get(report_type)
    if config is None:
        raise ValueError(f"Tipo de relatório '{report_type}' não registrado.")
    if not config.get("enabled"):
        raise ValueError(f"Tipo de relatório '{report_type}' não está habilitado.")

    key = config["key"]

    if key == "forecast":
        from services.validation_service import validate_forecast
        from services.forecast_service import normalize_forecast
        from services.upload_service import persist_validated_forecast
        return {**config, "validator": validate_forecast, "normalizer": normalize_forecast, "persist_trusted": persist_validated_forecast}

    if key == "stock":
        from services.stock_service import validate_stock_file, normalize_stock, persist_validated_stock
        return {**config, "validator": validate_stock_file, "normalizer": normalize_stock, "persist_trusted": persist_validated_stock}

    raise ValueError(f"Tipo de relatório '{report_type}' não possui implementação de serviço.")
