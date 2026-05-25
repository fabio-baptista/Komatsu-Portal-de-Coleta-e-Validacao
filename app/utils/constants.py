"""
constants.py

Constantes globais da aplicação.
Centraliza valores fixos como nomes de colunas esperadas no template,
status possíveis de envio, perfis de usuário, cores da identidade visual
e parâmetros de configuração do portal.
"""

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
