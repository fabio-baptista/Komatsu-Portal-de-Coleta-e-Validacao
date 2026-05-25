"""
validation_service.py

Serviço de validação do arquivo de forecast.
Concentra todas as regras de negócio de validação: estrutura, campos
obrigatórios, tipos de dados, formatos e compatibilidade com o fornecedor logado.

Não conecta com Snowflake. Toda validação é feita em memória com pandas.

Retorno padronizado (ValidationResult):
    is_valid             — True se o arquivo não possui nenhum erro
    normalized_dataframe — DataFrame com colunas canônicas, linhas vazias removidas
                           e quantidade normalizada como numérico
    errors_dataframe     — DataFrame com um erro por linha:
                           (linha, coluna, valor_informado, erro, orientacao_correcao)
    summary              — dict com contadores e metadados da validação

Ordem das validações:
    1.  Arquivo vazio
    2.  Colunas obrigatórias ausentes
    3.  Aliases de colunas aceitos (via normalize_columns)
    4.  Linhas totalmente vazias (removidas antes das demais checagens)
    5.  Material obrigatório
    6.  Filial / localidade obrigatória
    7.  Quantidade obrigatória
    8.  Quantidade numérica
    9.  Quantidade >= 0
    10. Data válida (múltiplos formatos aceitos)
    11. Fornecedor da planilha compatível com o fornecedor logado
        (executado apenas se a coluna existir no arquivo)
"""

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from utils.constants import COLUMN_ALIASES, REQUIRED_COLUMNS
from utils.file_reader import normalize_columns


# ---------------------------------------------------------------------------
# Constantes internas
# ---------------------------------------------------------------------------

# Aliases para a coluna opcional de nome do fornecedor na planilha
_SUPPLIER_COL_ALIASES: list[str] = [
    "Fornecedor", "FORNECEDOR", "fornecedor",
    "Supplier", "SUPPLIER", "supplier",
    "supplier_name", "nome_fornecedor", "Nome Fornecedor",
    "NOME_FORNECEDOR",
]

# Formatos de data aceitos (tentados em ordem na função _try_parse_date)
_DATE_FORMATS: list[str] = [
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d/%m/%y",
    "%Y%m%d",
]

# Colunas do errors_dataframe (snake_case — consistente com mock_data_service)
_ERR_COLS = ["linha", "coluna", "valor_informado", "erro", "orientacao_correcao"]


# ---------------------------------------------------------------------------
# Tipo de retorno
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """
    Resultado completo da validação de um arquivo de forecast.

    Atributos:
        is_valid             — True se o arquivo não tem nenhum erro
        normalized_dataframe — DataFrame limpo com colunas canônicas
        errors_dataframe     — DataFrame de erros com 5 colunas (snake_case)
        summary              — dict com métricas e mapeamento de colunas
    """
    is_valid:             bool
    normalized_dataframe: pd.DataFrame
    errors_dataframe:     pd.DataFrame
    summary:              dict


# ---------------------------------------------------------------------------
# Ponto de entrada público
# ---------------------------------------------------------------------------

def validate_forecast(
    df: pd.DataFrame,
    supplier_name: Optional[str] = None,
) -> ValidationResult:
    """
    Valida um DataFrame de forecast e retorna um ValidationResult.

    Parâmetros:
        df            — DataFrame lido do arquivo do fornecedor
        supplier_name — Nome do fornecedor logado (para validação cruzada).
                        Vem do session_state, nunca da planilha.
    """
    errors: list[dict] = []

    # ------------------------------------------------------------------ #
    # 1. Arquivo vazio                                                    #
    # ------------------------------------------------------------------ #
    if df is None or df.empty:
        return _build_result(
            errors=[_err(0, "—", "—",
                         "Arquivo vazio",
                         "O arquivo não contém dados. Verifique se enviou o arquivo correto.")],
            norm_df=pd.DataFrame(),
            total_rows=0,
            empty_removed=0,
            column_map={},
        )

    # ------------------------------------------------------------------ #
    # 2+3. Colunas obrigatórias e aliases                                 #
    # ------------------------------------------------------------------ #
    column_map = normalize_columns(df)
    missing = [c for c in REQUIRED_COLUMNS if c not in column_map]

    if missing:
        for col in missing:
            hints = ", ".join(_col_aliases(col)[:4])
            errors.append(_err(
                linha=0,
                coluna=col,
                valor="—",
                erro="Coluna obrigatória ausente",
                orientacao=(
                    f"Adicione a coluna '{col}' ao arquivo. "
                    f"Nomes aceitos: {hints}"
                ),
            ))
        # Sem as colunas obrigatórias não é possível validar linhas
        return _build_result(
            errors=errors,
            norm_df=pd.DataFrame(),
            total_rows=len(df),
            empty_removed=0,
            column_map=column_map,
        )

    # ------------------------------------------------------------------ #
    # 4. Linhas totalmente vazias                                         #
    # ------------------------------------------------------------------ #
    df_clean, empty_removed = _drop_empty_rows(df)

    if df_clean.empty:
        return _build_result(
            errors=[_err(0, "—", "—",
                         "Arquivo sem dados",
                         "Todas as linhas estão vazias. Preencha o template e reenvie.")],
            norm_df=pd.DataFrame(),
            total_rows=len(df),
            empty_removed=empty_removed,
            column_map=column_map,
        )

    # ------------------------------------------------------------------ #
    # Referências de colunas para validação por linha                     #
    # ------------------------------------------------------------------ #
    mat_col  = column_map["material"]
    qtd_col  = column_map["quantidade"]
    data_col = column_map["data_recebimento"]
    fil_col  = column_map["cidade_filial"]

    # Coluna de fornecedor (opcional — executa validação 11 se encontrada)
    sup_col = _detect_supplier_col(df_clean)

    invalid_indices: set = set()

    for idx, row in df_clean.iterrows():
        # Linha real no arquivo: cabeçalho ocupa linha 1, dados começam em 2
        linha = int(idx) + 2

        # -------------------------------------------------------------- #
        # 5. Material obrigatório                                         #
        # -------------------------------------------------------------- #
        mat_val = row[mat_col]
        if _is_empty(mat_val):
            errors.append(_err(linha, mat_col, "(vazio)",
                               "Campo obrigatório",
                               "Informe o código do material"))
            invalid_indices.add(idx)

        # -------------------------------------------------------------- #
        # 6. Filial / localidade obrigatória                              #
        # -------------------------------------------------------------- #
        fil_val = row[fil_col]
        if _is_empty(fil_val):
            errors.append(_err(linha, fil_col, "(vazio)",
                               "Campo obrigatório",
                               "Informe a filial ou localidade"))
            invalid_indices.add(idx)

        # -------------------------------------------------------------- #
        # 7 / 8 / 9. Quantidade: obrigatória, numérica, >= 0             #
        # -------------------------------------------------------------- #
        qtd_val = row[qtd_col]
        if _is_empty(qtd_val):
            errors.append(_err(linha, qtd_col, "(vazio)",
                               "Campo obrigatório",
                               "Informe a quantidade prevista"))
            invalid_indices.add(idx)
        else:
            try:
                num = float(str(qtd_val).replace(",", ".").strip())
                if num < 0:
                    errors.append(_err(linha, qtd_col, str(qtd_val),
                                       "Valor negativo",
                                       "A quantidade deve ser maior ou igual a zero"))
                    invalid_indices.add(idx)
            except (ValueError, TypeError):
                errors.append(_err(linha, qtd_col, str(qtd_val),
                                   "Tipo inválido",
                                   "Informe um valor numérico (ex: 10 ou 10.5)"))
                invalid_indices.add(idx)

        # -------------------------------------------------------------- #
        # 10. Data válida                                                 #
        # -------------------------------------------------------------- #
        date_val = row[data_col]
        if _is_empty(date_val):
            errors.append(_err(linha, data_col, "(vazio)",
                               "Campo obrigatório",
                               "Informe a data de recebimento"))
            invalid_indices.add(idx)
        elif not _is_valid_date(date_val):
            errors.append(_err(linha, data_col, str(date_val),
                               "Data inválida",
                               "Use o formato DD/MM/AAAA ou AAAA-MM-DD"))
            invalid_indices.add(idx)

        # -------------------------------------------------------------- #
        # 11. Fornecedor compatível (apenas se coluna existir e nome      #
        #     do fornecedor logado foi informado)                         #
        # -------------------------------------------------------------- #
        if sup_col and supplier_name:
            cell = row[sup_col]
            if not _is_empty(cell):
                cell_str = str(cell).strip()
                if not _supplier_match(cell_str, supplier_name):
                    errors.append(_err(
                        linha, sup_col, cell_str,
                        "Fornecedor incompatível",
                        (f"O arquivo deve pertencer a '{supplier_name}'. "
                         f"Valor encontrado na planilha: '{cell_str}'"),
                    ))
                    invalid_indices.add(idx)

    # ------------------------------------------------------------------ #
    # Construção do resultado final                                       #
    # ------------------------------------------------------------------ #
    norm_df = _normalize_df(df_clean, column_map)

    return _build_result(
        errors=errors,
        norm_df=norm_df,
        total_rows=len(df_clean),
        empty_removed=empty_removed,
        column_map=column_map,
        invalid_indices=invalid_indices,
    )


# ---------------------------------------------------------------------------
# Construção do resultado
# ---------------------------------------------------------------------------

def _build_result(
    errors: list[dict],
    norm_df: pd.DataFrame,
    total_rows: int,
    empty_removed: int,
    column_map: dict,
    invalid_indices: Optional[set] = None,
) -> ValidationResult:
    """Monta e retorna o ValidationResult final."""
    errors_df    = _to_errors_df(errors)
    invalid_rows = len(invalid_indices) if invalid_indices else (total_rows if errors else 0)
    valid_rows   = max(0, total_rows - invalid_rows)

    errors_by_type = (
        errors_df["erro"].value_counts().to_dict()
        if not errors_df.empty else {}
    )

    summary = {
        "total_rows":         total_rows,
        "empty_rows_removed": empty_removed,
        "valid_rows":         valid_rows,
        "invalid_rows":       invalid_rows,
        "column_map":         column_map,
        "errors_by_type":     errors_by_type,
    }

    return ValidationResult(
        is_valid=len(errors) == 0,
        normalized_dataframe=norm_df,
        errors_dataframe=errors_df,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Normalização do DataFrame
# ---------------------------------------------------------------------------

def _normalize_df(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    """
    Retorna cópia do DataFrame com:
    - Colunas renomeadas para nomes canônicos (ex: "Qtd" → "quantidade")
    - Linhas com quantidade inválida têm o campo convertido para NaN
    - Datas padronizadas para AAAA-MM-DD (valores inválidos mantidos como string)
    - Colunas extras (fora do mapeamento) são preservadas
    """
    df_out = df.copy()

    # Renomear apenas as colunas mapeadas
    rename_map = {real: canonical for canonical, real in column_map.items()}
    df_out = df_out.rename(columns=rename_map)

    # Normalizar quantidade para numérico
    if "quantidade" in df_out.columns:
        df_out["quantidade"] = pd.to_numeric(
            df_out["quantidade"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )

    # Normalizar data para AAAA-MM-DD
    if "data_recebimento" in df_out.columns:
        df_out["data_recebimento"] = df_out["data_recebimento"].apply(
            _parse_date_safe
        )

    return df_out


# ---------------------------------------------------------------------------
# Utilitários privados
# ---------------------------------------------------------------------------

def _err(
    linha: int,
    coluna: str,
    valor: str,
    erro: str,
    orientacao: str,
) -> dict:
    """Cria um dict de erro com as 5 colunas padronizadas."""
    return {
        "linha":             linha,
        "coluna":            coluna,
        "valor_informado":   valor,
        "erro":              erro,
        "orientacao_correcao": orientacao,
    }


def _to_errors_df(errors: list[dict]) -> pd.DataFrame:
    """Converte lista de erros para DataFrame com colunas padronizadas."""
    if not errors:
        return pd.DataFrame(columns=_ERR_COLS)
    return pd.DataFrame(errors, columns=_ERR_COLS)


def _is_empty(val) -> bool:
    """Retorna True se o valor é nulo ou string vazia."""
    if pd.isna(val):
        return True
    return str(val).strip() == ""


def _drop_empty_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove linhas onde todas as células são nulas ou vazias."""
    mask = df.apply(
        lambda row: all(_is_empty(v) for v in row), axis=1
    )
    removed = int(mask.sum())
    return df[~mask].copy(), removed


def _detect_supplier_col(df: pd.DataFrame) -> Optional[str]:
    """
    Detecta se o arquivo possui uma coluna de nome do fornecedor.
    Retorna o nome real da coluna ou None se não encontrado.
    """
    actual_lower = {col.strip().lower(): col for col in df.columns}
    for alias in _SUPPLIER_COL_ALIASES:
        if alias.strip().lower() in actual_lower:
            return actual_lower[alias.strip().lower()]
    return None


def _supplier_match(cell_value: str, logged_name: str) -> bool:
    """
    Verifica se o nome do fornecedor na célula é compatível com o logado.
    Aceita correspondência parcial (substring) em ambas as direções,
    case-insensitive, para cobrir variações como 'Vianmaq' vs 'Vianmaq S.A.'.
    """
    a = cell_value.strip().lower()
    b = logged_name.strip().lower()
    return a == b or a in b or b in a


def _is_valid_date(val) -> bool:
    """Tenta interpretar o valor como uma data nos formatos aceitos."""
    if isinstance(val, (pd.Timestamp,)):
        return True
    val_str = str(val).strip()
    for fmt in _DATE_FORMATS:
        try:
            pd.to_datetime(val_str, format=fmt)
            return True
        except (ValueError, TypeError):
            continue
    # Último recurso: parser genérico do pandas
    try:
        pd.to_datetime(val_str, dayfirst=True)
        return True
    except Exception:
        return False


def _parse_date_safe(val) -> str:
    """
    Tenta converter um valor para string de data ISO (AAAA-MM-DD).
    Retorna o valor original como string se não for possível converter.
    """
    if _is_empty(val):
        return ""
    if isinstance(val, pd.Timestamp):
        return val.strftime("%Y-%m-%d")
    val_str = str(val).strip()
    for fmt in _DATE_FORMATS:
        try:
            return pd.to_datetime(val_str, format=fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    try:
        return pd.to_datetime(val_str, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return val_str


def _col_aliases(canonical: str) -> list[str]:
    """Retorna a lista de aliases aceitos para uma coluna canônica."""
    return COLUMN_ALIASES.get(canonical, [canonical])


# ---------------------------------------------------------------------------
# Compatibilidade com código legado
# ---------------------------------------------------------------------------

def errors_to_dataframe(errors_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compatibilidade reversa: retorna o próprio errors_dataframe sem alteração.
    Mantido para evitar quebra em eventuais chamadas externas.
    """
    return errors_df
