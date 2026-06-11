"""
file_reader.py

Funções utilitárias de leitura de arquivos.
Responsável por detectar o formato (.xlsx ou .csv), ler o conteúdo
usando pandas e retornar um DataFrame padronizado para processamento.
"""

import io
import unicodedata
import pandas as pd
from utils.constants import COLUMN_ALIASES


def read_uploaded_file(
    uploaded_file,
) -> tuple[pd.DataFrame | None, str | None]:
    """
    Lê um arquivo .csv enviado e retorna (DataFrame, None) em caso de sucesso
    ou (None, mensagem_de_erro) em caso de falha.
    Uso exclusivo para CSV; para XLSX use read_excel_file().
    """
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        return None, f"Erro ao ler o arquivo CSV: {e}"

    if df.empty:
        return None, "O arquivo está vazio."

    return df, None


def read_excel_file(
    uploaded_file,
    sheet_name: str | int = 0,
) -> tuple[pd.DataFrame | None, list[str], str | None]:
    """
    Lê um arquivo .xlsx e retorna (DataFrame, lista_de_abas, None) em sucesso
    ou (None, [], mensagem_de_erro) em falha.

    Retorna a lista de abas para que a UI possa oferecer seleção ao usuário
    quando houver mais de uma aba.
    """
    try:
        xl = pd.ExcelFile(uploaded_file)
        sheet_names = xl.sheet_names
    except Exception as e:
        return None, [], f"Erro ao abrir o arquivo Excel: {e}"

    try:
        df = pd.read_excel(xl, sheet_name=sheet_name)
    except Exception as e:
        return None, sheet_names, f"Erro ao ler a aba '{sheet_name}': {e}"

    if df.empty:
        return None, sheet_names, "A aba selecionada está vazia."

    return df, sheet_names, None


def _normalize_header(s: str) -> str:
    """
    Normaliza nome de coluna para comparacao accent-insensitive e case-insensitive.
    strip, lowercase, remove acentos, underscores viram espacos, multiplos espacos viram um.
    """
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("_", " ")
    s = " ".join(s.split())
    return s


def normalize_columns(df: pd.DataFrame) -> dict[str, str]:
    """
    Mapeia nomes canônicos das colunas obrigatórias para os nomes reais
    encontrados no DataFrame.

    Usa normalização accent-insensitive e case-insensitive.

    Retorna um dicionário {canonical: nome_real} apenas para as colunas
    que foram de fato localizadas. Colunas ausentes não aparecem no resultado.
    """
    # Mapa: header normalizado -> nome original no DataFrame
    df_cols_norm = {_normalize_header(col): col for col in df.columns}
    found: dict[str, str] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            norm_alias = _normalize_header(alias)
            if norm_alias in df_cols_norm:
                found[canonical] = df_cols_norm[norm_alias]
                break

    return found


# ---------------------------------------------------------------------------
# Geração de relatório de correção para download
# ---------------------------------------------------------------------------

# Mapeamento de nomes de colunas snake_case → rótulos amigáveis para o XLSX
_ERROR_COL_LABELS: dict[str, str] = {
    "linha":                "Linha",
    "coluna":               "Coluna",
    "valor_informado":      "Valor Informado",
    "erro":                 "Erro",
    "orientacao_correcao":  "Orientação de Correção",
}


def build_error_report(
    errors_df: pd.DataFrame,
    name: str,
) -> tuple[bytes, str, str]:
    """
    Gera o relatório de correção como XLSX (preferencial) ou CSV (fallback).

    Parâmetros:
        errors_df — DataFrame de erros com colunas snake_case
        name      — identificador para o nome do arquivo (ex: upload_id ou nome do arquivo)

    Retorna:
        (data_bytes, filename, mime_type)

    XLSX é gerado com colunas renomeadas para rótulos amigáveis.
    Se openpyxl não estiver instalado, gera CSV como fallback.
    """
    try:
        import openpyxl  # noqa: F401 — verifica disponibilidade

        df_out = errors_df.rename(columns=_ERROR_COL_LABELS)
        buf = io.BytesIO()
        df_out.to_excel(
            buf,
            index=False,
            engine="openpyxl",
            sheet_name="Relatório de Correção",
        )
        buf.seek(0)
        return (
            buf.read(),
            f"relatorio_correcao_{name}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ImportError:
        return (
            errors_df.to_csv(index=False).encode("utf-8"),
            f"relatorio_correcao_{name}.csv",
            "text/csv",
        )
