"""
forecast_service.py

Serviço de acesso e normalização de dados de forecast.

Responsabilidades:
  1. Consultar registros validados (camada TRUSTED — mock ou Snowflake).
  2. Normalizar um DataFrame validado para o formato padronizado de STAGING/TRUSTED.
  3. Disponibilizar o mapeamento de aliases de colunas para documentação e UI.

Separação de responsabilidades:
  - validation_service.py → regras de validação (estrutura, tipos, obrigatoriedade)
  - forecast_service.py   → transformação para o formato final do esquema alvo

Dados mockados centralizados em services/mock_data_service.py.
Em produção: leitura/escrita em TRUSTED.forecast_validated (ou equivalente).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from services.mock_data_service import get_mock_validated_forecast
from utils.constants import COLUMN_ALIASES


# ---------------------------------------------------------------------------
# Esquema alvo (STAGING / TRUSTED)
# ---------------------------------------------------------------------------

# Colunas obrigatórias no DataFrame final normalizado
_FINAL_COLUMNS: list[str] = [
    "supplier_id",
    "supplier_name",
    "branch",
    "material_code",
    "material_description",
    "forecast_period",
    "forecast_quantity",
    "upload_id",
    "upload_version",
    "uploaded_at",
    "source_file_name",
    "is_active",
]

# Mapeamento: nome canônico (saída da validação) → nome final no esquema alvo
_CANONICAL_TO_SCHEMA: dict[str, str] = {
    "material":          "material_code",
    "quantidade":        "forecast_quantity",
    "data_recebimento":  "forecast_period",
    "cidade_filial":     "branch",
}

# Aliases para a coluna opcional de descrição do material
_DESC_COL_ALIASES: list[str] = [
    "descricao", "descricao_material", "description", "material_description",
    "Descrição", "Descricao", "DESCRICAO", "Description",
    "Desc Material", "Desc. Material", "Descrição Material",
]


# ---------------------------------------------------------------------------
# Mapa completo de aliases (canônico → variantes aceitas no arquivo)
# Inclui os campos do esquema final para referência e documentação.
# ---------------------------------------------------------------------------

_ALIAS_MAP: dict[str, list[str]] = {
    **COLUMN_ALIASES,  # aliases das colunas obrigatórias já definidos
    "material_description": _DESC_COL_ALIASES,
}


# ---------------------------------------------------------------------------
# Tipo de retorno da normalização
# ---------------------------------------------------------------------------

@dataclass
class NormalizationResult:
    """
    Resultado da normalização de um arquivo de forecast para o esquema alvo.

    Atributos:
        success           — True se a normalização foi concluída sem falhas
        staging_dataframe — DataFrame no formato final (12 colunas do esquema alvo)
        summary           — Métricas e metadados da normalização
        warnings          — Lista de avisos não bloqueantes (ex: coluna descrição ausente)
    """
    success:           bool
    staging_dataframe: pd.DataFrame
    summary:           dict
    warnings:          list[str]


# ---------------------------------------------------------------------------
# Função principal de normalização
# ---------------------------------------------------------------------------

def normalize_forecast(
    normalized_df: pd.DataFrame,
    supplier_id:      str,
    supplier_name:    str,
    upload_id:        str,
    upload_version:   int,
    source_file_name: str,
    uploaded_at:      Optional[str] = None,
) -> NormalizationResult:
    """
    Transforma o DataFrame validado (saída de validation_service) para o formato
    final do esquema alvo (STAGING / TRUSTED).

    Parâmetros:
        normalized_df    — DataFrame com colunas canônicas, vindo de
                           ValidationResult.normalized_dataframe
        supplier_id      — ID do fornecedor logado (ex: "SUP001").
                           Nunca vem da planilha — sempre do session_state.
        supplier_name    — Nome do fornecedor logado (ex: "Vianmaq").
                           Nunca vem da planilha — sempre do session_state.
        upload_id        — Identificador do upload (ex: "UP-002")
        upload_version   — Número da versão do envio (ex: 2)
        source_file_name — Nome original do arquivo enviado
        uploaded_at      — Data/hora do envio em ISO 8601. Se None, usa agora.

    Retorno:
        NormalizationResult com staging_dataframe no formato de 12 colunas.
    """
    warnings: list[str] = []

    # ------------------------------------------------------------------ #
    # Guarda de segurança                                                  #
    # ------------------------------------------------------------------ #
    if normalized_df is None or normalized_df.empty:
        return NormalizationResult(
            success=False,
            staging_dataframe=_empty_staging_df(),
            summary={"total_rows": 0, "upload_id": upload_id},
            warnings=["DataFrame de entrada está vazio. Nenhum dado normalizado."],
        )

    df = normalized_df.copy()

    # ------------------------------------------------------------------ #
    # 1. Renomear colunas canônicas → nomes do esquema alvo               #
    # ------------------------------------------------------------------ #
    df = df.rename(columns=_CANONICAL_TO_SCHEMA)

    # ------------------------------------------------------------------ #
    # 2. Detectar e mapear coluna de descrição (opcional)                  #
    # ------------------------------------------------------------------ #
    desc_col = _detect_col(df, _DESC_COL_ALIASES)
    if desc_col:
        df = df.rename(columns={desc_col: "material_description"})
    else:
        df["material_description"] = ""
        warnings.append(
            "Coluna de descrição do material não encontrada no arquivo. "
            "Campo 'material_description' preenchido como vazio."
        )

    # ------------------------------------------------------------------ #
    # 3. Adicionar colunas de metadados                                    #
    # Fornecedor vem do usuário logado — nunca da planilha.               #
    # ------------------------------------------------------------------ #
    ts = uploaded_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df["supplier_id"]      = supplier_id
    df["supplier_name"]    = supplier_name
    df["upload_id"]        = upload_id
    df["upload_version"]   = upload_version
    df["uploaded_at"]      = ts
    df["source_file_name"] = source_file_name
    df["is_active"]        = True

    # ------------------------------------------------------------------ #
    # 4. Garantir tipos corretos nas colunas do esquema                   #
    # ------------------------------------------------------------------ #
    if "forecast_quantity" in df.columns:
        df["forecast_quantity"] = pd.to_numeric(
            df["forecast_quantity"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        ).astype("Int64")  # nullable integer

    if "forecast_period" in df.columns:
        df["forecast_period"] = df["forecast_period"].astype(str).str.strip()

    if "material_code" in df.columns:
        df["material_code"] = df["material_code"].astype(str).str.strip()

    if "branch" in df.columns:
        df["branch"] = df["branch"].astype(str).str.strip()

    # ------------------------------------------------------------------ #
    # 5. Selecionar e reordenar apenas as colunas do esquema final        #
    # Colunas extras do arquivo original são descartadas nesta etapa.    #
    # ------------------------------------------------------------------ #
    missing_schema_cols = [c for c in _FINAL_COLUMNS if c not in df.columns]
    for col in missing_schema_cols:
        df[col] = None
        warnings.append(f"Coluna '{col}' ausente no esquema — preenchida com None.")

    staging_df = df[_FINAL_COLUMNS].reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # 6. Montar summary                                                   #
    # ------------------------------------------------------------------ #
    summary = {
        "total_rows":      len(staging_df),
        "supplier_id":     supplier_id,
        "supplier_name":   supplier_name,
        "upload_id":       upload_id,
        "upload_version":  upload_version,
        "source_file":     source_file_name,
        "uploaded_at":     ts,
        "periods":         sorted(staging_df["forecast_period"].dropna().unique().tolist()),
        "total_quantity":  int(staging_df["forecast_quantity"].sum(skipna=True)),
        "warnings_count":  len(warnings),
    }

    return NormalizationResult(
        success=True,
        staging_dataframe=staging_df,
        summary=summary,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Utilitário: aliases de colunas
# ---------------------------------------------------------------------------

def get_column_aliases() -> dict[str, list[str]]:
    """
    Retorna o mapa completo de aliases aceitos por coluna.

    Estrutura: {nome_final_no_esquema: [alias1, alias2, ...]}

    Usado pela UI para exibir orientações ao fornecedor e por ferramentas
    de documentação do template.
    """
    return {
        "material_code":      COLUMN_ALIASES.get("material", []),
        "forecast_quantity":  COLUMN_ALIASES.get("quantidade", []),
        "forecast_period":    COLUMN_ALIASES.get("data_recebimento", []),
        "branch":             COLUMN_ALIASES.get("cidade_filial", []),
        "material_description": _DESC_COL_ALIASES,
    }


# ---------------------------------------------------------------------------
# Utilitários privados
# ---------------------------------------------------------------------------

def _detect_col(df: pd.DataFrame, aliases: list[str]) -> Optional[str]:
    """
    Detecta se o DataFrame possui uma coluna cujo nome está na lista de aliases.
    Comparação case-insensitive. Retorna o nome real da coluna ou None.
    """
    actual_lower = {col.strip().lower(): col for col in df.columns}
    for alias in aliases:
        key = alias.strip().lower()
        if key in actual_lower:
            return actual_lower[key]
    return None


def _empty_staging_df() -> pd.DataFrame:
    """Retorna um DataFrame vazio com o esquema alvo completo."""
    return pd.DataFrame(columns=_FINAL_COLUMNS)


# ---------------------------------------------------------------------------
# ForecastRecord — mantido para compatibilidade com tela de dados validados
# ---------------------------------------------------------------------------

@dataclass
class ForecastRecord:
    """Representa uma linha de forecast validado na camada TRUSTED."""
    supplier:      str
    branch:        str
    material_code: str
    description:   str
    period:        str
    qty:           int
    version:       int
    processed_at:  str
    source_file:   str


def _dict_to_record(d: dict) -> ForecastRecord:
    return ForecastRecord(
        supplier=      d["supplier"],
        branch=        d["branch"],
        material_code= d["material_code"],
        description=   d["description"],
        period=        d["period"],
        qty=           d["qty"],
        version=       d["version"],
        processed_at=  d["processed_at"],
        source_file=   d["source_file"],
    )


def get_all_records() -> list[ForecastRecord]:
    """Retorna todos os registros validados (simulação da camada TRUSTED)."""
    return [_dict_to_record(d) for d in get_mock_validated_forecast()]


def get_filter_options() -> dict:
    """Retorna valores únicos disponíveis para cada filtro da tela."""
    records = get_all_records()
    return {
        "suppliers":  sorted({r.supplier for r in records}),
        "branches":   sorted({r.branch for r in records}),
        "periods":    sorted({r.period for r in records}, reverse=True),
        "versions":   sorted({r.version for r in records}, reverse=True),
    }


def filter_records(
    records: list[ForecastRecord],
    supplier:      str | None = None,
    branch:        str | None = None,
    material_code: str | None = None,
    period:        str | None = None,
    version:       int | None = None,
) -> list[ForecastRecord]:
    """
    Aplica filtros à lista de registros.
    Filtros com valor None ou string vazia são ignorados.
    """
    result = records

    if supplier:
        result = [r for r in result if r.supplier == supplier]
    if branch:
        result = [r for r in result if r.branch == branch]
    if material_code and material_code.strip():
        q = material_code.strip().lower()
        result = [r for r in result
                  if q in r.material_code.lower() or q in r.description.lower()]
    if period:
        result = [r for r in result if r.period == period]
    if version is not None:
        result = [r for r in result if r.version == version]

    return result


def get_summary(records: list[ForecastRecord]) -> dict:
    """Retorna métricas consolidadas para os cards de resumo."""
    suppliers = {r.supplier for r in records}
    periods   = {r.period for r in records}
    versions  = {r.version for r in records}

    return {
        "total":          len(records),
        "suppliers":      len(suppliers),
        "period_label":   ", ".join(sorted(periods, reverse=True)) if periods else "—",
        "active_version": max(versions) if versions else "—",
    }


# ---------------------------------------------------------------------------
# Leitura de forecasts validados do Snowflake — TRUSTED.FORECAST_VALIDATED
# ---------------------------------------------------------------------------

_DATABASE = "KBI_DATA_JOURNEY_DEV_DB"


def get_validated_forecasts_from_snowflake() -> list[dict]:
    """
    Lê forecasts ativos de TRUSTED.FORECAST_VALIDATED no Snowflake.

    Retorna list[dict] no formato esperado pela UI de validated_data.py:
        supplier, branch, material_code, description, period, _period_key,
        qty, version, processed_at, source_file, _source

    Retorna lista vazia se não encontrar dados ou se a sessão estiver indisponível.
    """
    from services.snowflake_service import get_snowflake_session
    from utils.logger import get_logger
    from utils.dates import format_period_pt

    logger = get_logger(__name__)

    logger.info("get_validated_forecasts_from_snowflake: consultando TRUSTED...")

    session = get_snowflake_session()
    if session is None:
        logger.error(
            "get_validated_forecasts_from_snowflake: sessão Snowflake indisponível."
        )
        return []

    query = f"""
        SELECT SUPPLIER_NAME, BRANCH, MATERIAL_CODE, MATERIAL_DESCRIPTION,
               FORECAST_PERIOD, FORECAST_QUANTITY, UPLOAD_VERSION,
               UPLOADED_AT, SOURCE_FILE_NAME
        FROM {_DATABASE}.TRUSTED.FORECAST_VALIDATED
        WHERE IS_ACTIVE = TRUE
        ORDER BY UPLOADED_AT DESC
    """

    try:
        import pandas as pd
        df = session.sql(query).to_pandas()
    except Exception as exc:
        logger.error(
            "get_validated_forecasts_from_snowflake: falha na query.\n"
            "  erro: %s\n  tipo: %s",
            exc, type(exc).__name__,
        )
        return []

    if df is None or df.empty:
        logger.info(
            "get_validated_forecasts_from_snowflake: nenhum registro ativo encontrado."
        )
        return []

    # Mapear colunas Snowflake → formato UI
    rows: list[dict] = []
    for _, row in df.iterrows():
        # FORECAST_PERIOD é DATE — converter para string "YYYY-MM-DD"
        period_raw = str(row["FORECAST_PERIOD"])[:10] if row["FORECAST_PERIOD"] else "—"

        # FORECAST_QUANTITY
        try:
            qty_val = int(float(row["FORECAST_QUANTITY"]))
        except (TypeError, ValueError):
            qty_val = 0

        # UPLOADED_AT — formatar como string
        uploaded_at = row["UPLOADED_AT"]
        try:
            import pandas as _pd
            ts = _pd.Timestamp(uploaded_at)
            processed_at = ts.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            processed_at = str(uploaded_at)[:19] if uploaded_at else "—"

        rows.append({
            "supplier":      str(row["SUPPLIER_NAME"]) if row["SUPPLIER_NAME"] else "—",
            "branch":        str(row["BRANCH"]) if row["BRANCH"] else "—",
            "material_code": str(row["MATERIAL_CODE"]) if row["MATERIAL_CODE"] else "—",
            "description":   str(row["MATERIAL_DESCRIPTION"]) if row["MATERIAL_DESCRIPTION"] else "—",
            "period":        format_period_pt(period_raw),
            "_period_key":   period_raw,
            "qty":           qty_val,
            "version":       int(row["UPLOAD_VERSION"]),
            "processed_at":  processed_at,
            "source_file":   str(row["SOURCE_FILE_NAME"]) if row["SOURCE_FILE_NAME"] else "—",
            "_source":       "snowflake",
        })

    logger.info(
        "get_validated_forecasts_from_snowflake: %d registros ativos retornados.",
        len(rows),
    )
    return rows
