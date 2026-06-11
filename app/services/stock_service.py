"""
stock_service.py

Service dedicado para validacao, normalizacao e persistencia de relatorios de Estoque.
Segue o mesmo contrato de interfaces de forecast_service/validation_service para
compatibilidade com supplier_upload.py via REPORT_TYPE_REGISTRY.
"""

import uuid
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from utils.constants import STOCK_COLUMN_ALIASES, STOCK_REQUIRED_COLUMNS
from utils.logger import get_logger

_logger = get_logger(__name__)

_DATABASE = "KBI_DATA_JOURNEY_DEV_DB"

# Colunas finais do schema alvo (TRUSTED.STOCK_VALIDATED)
_FINAL_COLUMNS = [
    "supplier_id", "supplier_name", "branch", "material_code",
    "material_description", "stock_quantity", "unit_cost", "total_cost",
    "purchase_date", "last_sale_date", "invoice_number",
    "stock_year", "stock_month",
    "upload_id", "upload_version", "uploaded_at", "source_file_name", "is_active",
]


# ---------------------------------------------------------------------------
# Dataclasses compatíveis com ValidationResult / NormalizationResult
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    is_valid: bool
    normalized_dataframe: pd.DataFrame
    errors_dataframe: pd.DataFrame
    summary: dict


@dataclass
class NormalizationResult:
    success: bool
    staging_dataframe: pd.DataFrame
    summary: dict
    warnings: list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_header(s: str) -> str:
    """
    Normaliza nome de coluna para comparacao accent-insensitive e case-insensitive.
    - strip
    - lowercase
    - remove acentos (NFD + strip combining)
    - underscores viram espacos
    - multiplos espacos viram um
    """
    s = s.strip().lower()
    # Remove acentos
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # Underscores viram espacos
    s = s.replace("_", " ")
    # Multiplos espacos
    s = " ".join(s.split())
    return s


def _resolve_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """
    Mapeia nomes canonicos para nomes reais no DataFrame usando STOCK_COLUMN_ALIASES.
    Usa normalizacao accent-insensitive para comparacao.
    Retorna dict { canonical_name: real_column_name | None }.
    """
    # Mapa: header normalizado -> nome real no DataFrame
    df_cols_norm = {_normalize_header(c): c for c in df.columns}
    resolved = {}

    for canonical, aliases in STOCK_COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            norm_alias = _normalize_header(alias)
            if norm_alias in df_cols_norm:
                found = df_cols_norm[norm_alias]
                break
        resolved[canonical] = found

    return resolved


def _err(row: int, col: str, value: str, error: str, fix: str) -> dict:
    return {
        "linha": row,
        "coluna": col,
        "valor_informado": value,
        "erro": error,
        "orientacao_correcao": fix,
    }


def _is_numeric(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    try:
        float(str(val).replace(",", ".").strip())
        return True
    except (ValueError, TypeError):
        return False


def _to_float(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def _is_valid_date(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    if isinstance(val, (datetime,)):
        return True
    if isinstance(val, pd.Timestamp):
        return True
    s = str(val).strip()
    if not s or s in ("(vazio)", "—", "-", "NaT"):
        return False
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            continue
    try:
        pd.to_datetime(s, dayfirst=True, errors="raise")
        return True
    except Exception:
        return False


def _parse_date(val) -> Optional[str]:
    """Converte valor para YYYY-MM-DD string ou None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s or s in ("(vazio)", "—", "-", "NaT"):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        return pd.to_datetime(s, dayfirst=True, errors="raise").strftime("%Y-%m-%d")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

def validate_stock_file(
    df: pd.DataFrame,
    supplier_name: Optional[str] = None,
) -> ValidationResult:
    """
    Valida um DataFrame de estoque.
    Mesma interface que validate_forecast() para compatibilidade com supplier_upload.py.
    """
    errors: list[dict] = []

    # 1. Arquivo vazio
    if df is None or df.empty:
        return ValidationResult(
            is_valid=False,
            normalized_dataframe=pd.DataFrame(),
            errors_dataframe=pd.DataFrame([
                _err(0, "—", "—", "Arquivo vazio",
                     "O arquivo não contém dados. Verifique se enviou o arquivo correto.")
            ]),
            summary={"total_rows": 0, "valid_rows": 0, "invalid_rows": 0,
                     "empty_removed": 0, "column_map": {}},
        )

    # 2. Resolver colunas via aliases
    col_map = _resolve_columns(df)

    # 3. Verificar colunas obrigatórias
    missing = [c for c in STOCK_REQUIRED_COLUMNS if col_map.get(c) is None]
    if missing:
        missing_labels = ", ".join(missing)
        return ValidationResult(
            is_valid=False,
            normalized_dataframe=pd.DataFrame(),
            errors_dataframe=pd.DataFrame([
                _err(0, missing_labels, "—",
                     f"Coluna(s) obrigatória(s) não encontrada(s): {missing_labels}",
                     "Verifique se o arquivo possui as colunas: "
                     + ", ".join(STOCK_REQUIRED_COLUMNS))
            ]),
            summary={"total_rows": len(df), "valid_rows": 0,
                     "invalid_rows": len(df), "empty_removed": 0,
                     "column_map": col_map},
        )

    # 4. Remover linhas totalmente vazias
    df_clean = df.dropna(how="all").reset_index(drop=True)
    empty_removed = len(df) - len(df_clean)

    # 5. Validar linha a linha
    for idx, row in df_clean.iterrows():
        line_num = idx + 2  # +2 porque idx=0 é primeira linha de dados, +1 cabeçalho

        # material_code obrigatório
        mat_col = col_map["material_code"]
        mat_val = row.get(mat_col, None)
        if mat_val is None or (isinstance(mat_val, float) and pd.isna(mat_val)) or str(mat_val).strip() == "":
            errors.append(_err(line_num, "material_code", "(vazio)",
                              "Campo obrigatorio", "Informar o codigo do material"))

        # branch obrigatório
        br_col = col_map["branch"]
        br_val = row.get(br_col, None)
        if br_val is None or (isinstance(br_val, float) and pd.isna(br_val)) or str(br_val).strip() == "":
            errors.append(_err(line_num, "branch", "(vazio)",
                              "Campo obrigatorio", "Informar a filial"))

        # stock_quantity numérico >= 0
        qty_col = col_map["stock_quantity"]
        qty_val = row.get(qty_col, None)
        if qty_val is None or (isinstance(qty_val, float) and pd.isna(qty_val)) or str(qty_val).strip() == "":
            errors.append(_err(line_num, "stock_quantity", "(vazio)",
                              "Campo obrigatorio", "Informar a quantidade em estoque"))
        elif not _is_numeric(qty_val):
            errors.append(_err(line_num, "stock_quantity", str(qty_val),
                              "Tipo invalido", "Informar valor numerico"))
        elif _to_float(qty_val) is not None and _to_float(qty_val) < 0:
            errors.append(_err(line_num, "stock_quantity", str(qty_val),
                              "Valor negativo", "Quantidade deve ser >= 0"))

        # unit_cost numérico >= 0
        uc_col = col_map["unit_cost"]
        uc_val = row.get(uc_col, None)
        if uc_val is None or (isinstance(uc_val, float) and pd.isna(uc_val)) or str(uc_val).strip() == "":
            errors.append(_err(line_num, "unit_cost", "(vazio)",
                              "Campo obrigatorio", "Informar o custo unitario"))
        elif not _is_numeric(uc_val):
            errors.append(_err(line_num, "unit_cost", str(uc_val),
                              "Tipo invalido", "Informar valor numerico"))
        elif _to_float(uc_val) is not None and _to_float(uc_val) < 0:
            errors.append(_err(line_num, "unit_cost", str(uc_val),
                              "Valor negativo", "Custo unitario deve ser >= 0"))

        # total_cost (opcional) — se presente e preenchido, validar numerico >= 0
        tc_col = col_map.get("total_cost")
        if tc_col:
            tc_val = row.get(tc_col, None)
            if tc_val is not None and not (isinstance(tc_val, float) and pd.isna(tc_val)) and str(tc_val).strip() != "":
                if not _is_numeric(tc_val):
                    errors.append(_err(line_num, "total_cost", str(tc_val),
                                      "Tipo invalido", "Informar valor numerico"))
                elif _to_float(tc_val) is not None and _to_float(tc_val) < 0:
                    errors.append(_err(line_num, "total_cost", str(tc_val),
                                      "Valor negativo", "Custo total deve ser >= 0"))

        # purchase_date — data válida obrigatória
        pd_col = col_map["purchase_date"]
        pd_val = row.get(pd_col, None)
        if pd_val is None or (isinstance(pd_val, float) and pd.isna(pd_val)) or str(pd_val).strip() == "":
            errors.append(_err(line_num, "purchase_date", "(vazio)",
                              "Campo obrigatorio", "Informar a data de compra"))
        elif not _is_valid_date(pd_val):
            errors.append(_err(line_num, "purchase_date", str(pd_val),
                              "Data invalida", "Informar data valida (DD/MM/AAAA ou AAAA-MM-DD)"))

        # last_sale_date — opcional, mas se preenchida deve ser válida
        lsd_col = col_map.get("last_sale_date")
        if lsd_col:
            lsd_val = row.get(lsd_col, None)
            if lsd_val is not None and not (isinstance(lsd_val, float) and pd.isna(lsd_val)) and str(lsd_val).strip() != "":
                if not _is_valid_date(lsd_val):
                    errors.append(_err(line_num, "last_sale_date", str(lsd_val),
                                      "Data invalida", "Informar data valida (DD/MM/AAAA ou AAAA-MM-DD)"))

    # Resultado
    total_rows = len(df_clean)
    invalid_rows = len({e["linha"] for e in errors})
    valid_rows = total_rows - invalid_rows

    is_valid = len(errors) == 0

    errors_df = pd.DataFrame(errors) if errors else pd.DataFrame(
        columns=["linha", "coluna", "valor_informado", "erro", "orientacao_correcao"]
    )

    return ValidationResult(
        is_valid=is_valid,
        normalized_dataframe=df_clean,
        errors_dataframe=errors_df,
        summary={
            "total_rows": total_rows,
            "valid_rows": valid_rows if is_valid else 0,
            "invalid_rows": invalid_rows if not is_valid else 0,
            "empty_removed": empty_removed,
            "column_map": col_map,
        },
    )


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def normalize_stock(
    normalized_df: pd.DataFrame,
    supplier_id: str,
    supplier_name: str,
    upload_id: str,
    upload_version: int,
    source_file_name: str,
    uploaded_at: Optional[str] = None,
) -> NormalizationResult:
    """
    Transforma DataFrame validado de Estoque para o schema alvo (TRUSTED.STOCK_VALIDATED).
    Mesma interface que normalize_forecast() para compatibilidade.
    """
    warnings: list[str] = []

    if normalized_df is None or normalized_df.empty:
        return NormalizationResult(
            success=True,
            staging_dataframe=pd.DataFrame(columns=_FINAL_COLUMNS),
            summary={"rows": 0},
            warnings=["DataFrame vazio — nenhuma linha para normalizar."],
        )

    col_map = _resolve_columns(normalized_df)

    # Construir DataFrame final
    rows = []
    for _, row in normalized_df.iterrows():
        mat_code = str(row.get(col_map["material_code"], "") or "").strip()
        mat_desc = ""
        if col_map.get("material_description"):
            mat_desc = str(row.get(col_map["material_description"], "") or "").strip()

        branch_val = str(row.get(col_map["branch"], "") or "").strip()
        qty = _to_float(row.get(col_map["stock_quantity"], 0))
        uc = _to_float(row.get(col_map["unit_cost"], 0))

        # total_cost: usa coluna se existir, senão calcula
        tc = None
        if col_map.get("total_cost"):
            tc = _to_float(row.get(col_map["total_cost"], None))
        if tc is None and qty is not None and uc is not None:
            tc = qty * uc

        # Datas
        pdate = _parse_date(row.get(col_map["purchase_date"], None)) if col_map.get("purchase_date") else None
        lsdate = None
        if col_map.get("last_sale_date"):
            lsdate = _parse_date(row.get(col_map["last_sale_date"], None))

        # Invoice
        inv = None
        if col_map.get("invoice_number"):
            inv = str(row.get(col_map["invoice_number"], "") or "").strip() or None

        # Year/Month
        yr = None
        mo = None
        if col_map.get("year"):
            try:
                yr = int(float(str(row.get(col_map["year"], "")).strip()))
            except (ValueError, TypeError):
                yr = None
        if col_map.get("month"):
            try:
                mo = int(float(str(row.get(col_map["month"], "")).strip()))
            except (ValueError, TypeError):
                mo = None

        # Supplier name da planilha (override se tiver coluna DB/Distribuidor)
        sup_name = supplier_name
        if col_map.get("supplier_name"):
            file_sup = str(row.get(col_map["supplier_name"], "") or "").strip()
            if file_sup:
                sup_name = file_sup

        rows.append({
            "supplier_id": supplier_id,
            "supplier_name": sup_name,
            "branch": branch_val,
            "material_code": mat_code,
            "material_description": mat_desc,
            "stock_quantity": qty,
            "unit_cost": uc,
            "total_cost": tc,
            "purchase_date": pdate,
            "last_sale_date": lsdate,
            "invoice_number": inv,
            "stock_year": yr,
            "stock_month": mo,
            "upload_id": upload_id,
            "upload_version": upload_version,
            "uploaded_at": uploaded_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file_name": source_file_name,
            "is_active": True,
        })

    staging_df = pd.DataFrame(rows, columns=_FINAL_COLUMNS)

    if col_map.get("material_description") is None:
        warnings.append("Coluna 'Descricao' não encontrada — campo ficará vazio.")

    return NormalizationResult(
        success=True,
        staging_dataframe=staging_df,
        summary={"rows": len(staging_df)},
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Persistência em TRUSTED.STOCK_VALIDATED
# ---------------------------------------------------------------------------

def persist_validated_stock(
    upload_id: str,
    supplier_id: str,
    supplier_name: str,
    upload_version: int,
    source_file_name: str,
    staging_df: pd.DataFrame,
) -> int:
    """
    Persiste linhas normalizadas de Estoque em TRUSTED.STOCK_VALIDATED.
    Mesma interface que persist_validated_forecast() para compatibilidade.

    Retorna quantidade de linhas inseridas (0 se falhar).
    """
    if staging_df is None or len(staging_df) == 0:
        _logger.info("persist_validated_stock: DataFrame vazio — nada a inserir.")
        return 0

    try:
        from services.snowflake_service import get_snowflake_session
        session = get_snowflake_session()
        if session is None:
            _logger.error("persist_validated_stock: sessao Snowflake indisponivel.")
            return 0

        # Desativar linhas anteriores do mesmo fornecedor
        safe_supplier = supplier_id.replace("'", "''")
        session.sql(f"""
            UPDATE {_DATABASE}.TRUSTED.STOCK_VALIDATED
            SET IS_ACTIVE = FALSE
            WHERE SUPPLIER_ID = '{safe_supplier}'
              AND IS_ACTIVE = TRUE
              AND UPLOAD_ID != '{upload_id.replace("'", "''")}'
        """).collect()

        # Inserir novas linhas
        count = 0
        for _, row in staging_df.iterrows():
            row_id = str(uuid.uuid4())
            mat_code = str(row.get("material_code", "")).replace("'", "''")
            mat_desc = str(row.get("material_description", "") or "").replace("'", "''")
            branch = str(row.get("branch", "")).replace("'", "''")
            qty = row.get("stock_quantity") or 0
            uc = row.get("unit_cost") or 0
            tc = row.get("total_cost") or 0
            p_date = row.get("purchase_date")
            ls_date = row.get("last_sale_date")
            inv = str(row.get("invoice_number") or "").replace("'", "''")
            s_year = row.get("stock_year")
            s_month = row.get("stock_month")
            uploaded_at = str(row.get("uploaded_at", "")).replace("'", "''")
            sfn = str(row.get("source_file_name", "")).replace("'", "''")

            p_date_sql = f"'{p_date}'" if p_date else "NULL"
            ls_date_sql = f"'{ls_date}'" if ls_date else "NULL"
            year_sql = str(int(s_year)) if s_year is not None else "NULL"
            month_sql = str(int(s_month)) if s_month is not None else "NULL"
            inv_sql = f"'{inv}'" if inv else "NULL"

            insert_sql = f"""
                INSERT INTO {_DATABASE}.TRUSTED.STOCK_VALIDATED (
                    ROW_ID, SUPPLIER_ID, SUPPLIER_NAME, BRANCH,
                    MATERIAL_CODE, MATERIAL_DESCRIPTION,
                    STOCK_QUANTITY, UNIT_COST, TOTAL_COST,
                    PURCHASE_DATE, LAST_SALE_DATE, INVOICE_NUMBER,
                    STOCK_YEAR, STOCK_MONTH,
                    UPLOAD_ID, UPLOAD_VERSION, UPLOADED_AT,
                    SOURCE_FILE_NAME, IS_ACTIVE, CREATED_AT
                ) VALUES (
                    '{row_id}', '{safe_supplier}', '{supplier_name.replace("'", "''")}', '{branch}',
                    '{mat_code}', '{mat_desc}',
                    {qty}, {uc}, {tc},
                    {p_date_sql}, {ls_date_sql}, {inv_sql},
                    {year_sql}, {month_sql},
                    '{upload_id.replace("'", "''")}', {upload_version}, '{uploaded_at}',
                    '{sfn}', TRUE, CURRENT_TIMESTAMP()
                )
            """
            session.sql(insert_sql).collect()
            count += 1

        _logger.info(
            "persist_validated_stock: %d linhas inseridas para upload_id=%s",
            count, upload_id,
        )
        return count

    except Exception as exc:
        _logger.exception("persist_validated_stock falhou: %s", exc)
        return 0
