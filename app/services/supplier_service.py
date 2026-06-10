"""
supplier_service.py

Servico de dados de fornecedores.
Le e grava fornecedores na tabela CONTROL.SUPPLIERS via Snowflake.
"""

import math
from dataclasses import dataclass, field
from typing import Optional

from services.snowflake_service import execute_query, get_snowflake_session
from utils.logger import get_logger

logger = get_logger(__name__)

DATABASE = "KBI_DATA_JOURNEY_DEV_DB"


@dataclass
class SupplierRecord:
    supplier_id: str
    code: str
    name: str
    email: str
    status: str
    last_upload: str = "—"
    period_status: str = "pending"
    recent_uploads: list = field(default_factory=list)


def _row_to_record(row: dict) -> SupplierRecord:
    last_upload   = str(row["LAST_UPLOAD"]).strip() if row.get("LAST_UPLOAD") else "—"
    period_status = str(row.get("PERIOD_STATUS", "pending") or "pending")
    return SupplierRecord(
        supplier_id=row["SUPPLIER_ID"],
        code=row["SUPPLIER_CODE"],
        name=row["SUPPLIER_NAME"],
        email=row["EMAIL"],
        status=row["STATUS"],
        last_upload=last_upload,
        period_status=period_status,
    )


def get_all_suppliers() -> list[SupplierRecord]:
    df = execute_query(f"""
        SELECT
            s.SUPPLIER_ID, s.SUPPLIER_CODE, s.SUPPLIER_NAME, s.EMAIL, s.STATUS,
            COALESCE(TO_CHAR(MAX(ub.UPLOADED_AT), 'DD/MM/YYYY HH24:MI'), '—') as LAST_UPLOAD,
            CASE
                WHEN MAX(CASE WHEN ub.STATUS = 'VALID' AND ub.IS_ACTIVE THEN 1 END) = 1 THEN 'valid'
                WHEN MAX(CASE WHEN ub.STATUS = 'INVALID' THEN 1 END) = 1 THEN 'invalid'
                WHEN s.STATUS = 'inactive' THEN 'not_expected'
                ELSE 'pending'
            END as PERIOD_STATUS
        FROM {DATABASE}.CONTROL.SUPPLIERS s
        LEFT JOIN {DATABASE}.CONTROL.UPLOAD_BATCHES ub ON s.SUPPLIER_ID = ub.SUPPLIER_ID
        GROUP BY s.SUPPLIER_ID, s.SUPPLIER_CODE, s.SUPPLIER_NAME, s.EMAIL, s.STATUS
        ORDER BY s.SUPPLIER_CODE
    """)
    if df is None or df.empty:
        return []
    return [_row_to_record(row) for _, row in df.iterrows()]


def get_supplier_by_code(code: str) -> Optional[SupplierRecord]:
    df = execute_query(
        f"SELECT * FROM {DATABASE}.CONTROL.SUPPLIERS WHERE UPPER(SUPPLIER_CODE) = :code",
        params={"code": code.strip().upper()},
    )
    if df is None or df.empty:
        return None
    return _row_to_record(df.iloc[0].to_dict())


def get_supplier_by_email(email: str) -> Optional[SupplierRecord]:
    df = execute_query(
        f"SELECT * FROM {DATABASE}.CONTROL.SUPPLIERS WHERE LOWER(EMAIL) = :email",
        params={"email": email.strip().lower()},
    )
    if df is None or df.empty:
        return None
    return _row_to_record(df.iloc[0].to_dict())


def get_supplier_by_id(supplier_id: str) -> Optional[SupplierRecord]:
    df = execute_query(
        f"SELECT * FROM {DATABASE}.CONTROL.SUPPLIERS WHERE SUPPLIER_ID = :sid",
        params={"sid": supplier_id},
    )
    if df is None or df.empty:
        return None
    return _row_to_record(df.iloc[0].to_dict())


def get_next_supplier_code() -> str:
    df = execute_query(
        f"""SELECT MAX(CAST(REPLACE(SUPPLIER_CODE, 'SUP', '') AS INTEGER)) as MAX_NUM
            FROM {DATABASE}.CONTROL.SUPPLIERS
            WHERE SUPPLIER_CODE LIKE 'SUP%'"""
    )
    if df is None or df.empty:
        return "SUP001"
    max_num = _safe_int(df.iloc[0]["MAX_NUM"], 0)
    if max_num == 0:
        return "SUP001"
    return f"SUP{max_num + 1:03d}"


def create_supplier(name: str, email: str, status: str = "active") -> Optional[SupplierRecord]:
    import uuid
    supplier_id = str(uuid.uuid4())[:36]
    code = get_next_supplier_code()
    logger.info("create_supplier: name=%s, email=%s, code=%s", name, email, code)

    session = get_snowflake_session()
    if session is None:
        logger.error(
            "create_supplier falhou: sessão Snowflake indisponível. "
            "Verifique logs de snowflake_service para detalhes da conexão."
        )
        return None

    # Escape single quotes to prevent SQL errors
    safe_name = name.replace("'", "''")
    safe_email = email.replace("'", "''")
    safe_status = status.replace("'", "''")

    sql = (
        f"INSERT INTO {DATABASE}.CONTROL.SUPPLIERS"
        f" (SUPPLIER_ID, SUPPLIER_CODE, SUPPLIER_NAME, EMAIL, STATUS)"
        f" VALUES ('{supplier_id}', '{code}', '{safe_name}', '{safe_email}', '{safe_status}')"
    )

    try:
        session.sql(sql).collect()
    except Exception as exc:
        logger.error(
            "create_supplier falhou ao executar INSERT.\n"
            "  SQL: %s\n"
            "  erro: %s\n"
            "  tipo: %s\n"
            "  Possíveis causas:\n"
            "    - Tabela %s.CONTROL.SUPPLIERS não existe\n"
            "    - Colunas incompatíveis com o DDL real\n"
            "    - Role/warehouse sem permissão de INSERT\n"
            "    - Database/schema errado na sessão",
            sql[:300], exc, type(exc).__name__, DATABASE,
        )
        return None

    return SupplierRecord(
        supplier_id=supplier_id,
        code=code,
        name=name,
        email=email,
        status=status,
    )


def update_supplier_status(supplier_id: str, new_status: str) -> bool:
    session = get_snowflake_session()
    if session is None:
        return False
    session.sql(f"""
        UPDATE {DATABASE}.CONTROL.SUPPLIERS
        SET STATUS = '{new_status}', UPDATED_AT = CURRENT_TIMESTAMP()
        WHERE SUPPLIER_ID = '{supplier_id}'
    """).collect()
    return True


def _safe_int(value, default: int = 0) -> int:
    """Converte valor para int de forma segura, tratando None, NaN e strings vazias."""
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def get_summary() -> dict:
    df = execute_query(
        f"""SELECT
                SUM(CASE WHEN STATUS = 'active' THEN 1 ELSE 0 END)   as TOTAL_ACTIVE,
                SUM(CASE WHEN STATUS = 'inactive' THEN 1 ELSE 0 END) as TOTAL_INACTIVE
            FROM {DATABASE}.CONTROL.SUPPLIERS"""
    )
    if df is None or df.empty:
        return {"total_active": 0, "total_inactive": 0}
    row = df.iloc[0].to_dict()
    return {
        "total_active":   _safe_int(row.get("TOTAL_ACTIVE")),
        "total_inactive": _safe_int(row.get("TOTAL_INACTIVE")),
    }


def update_supplier(supplier_id: str, name: str, email: str, status: str) -> bool:
    session = get_snowflake_session()
    if session is None:
        return False
    safe_name = name.replace("'", "''")
    safe_email = email.replace("'", "''")
    safe_status = status.replace("'", "''")
    session.sql(f"""
        UPDATE {DATABASE}.CONTROL.SUPPLIERS
        SET SUPPLIER_NAME = '{safe_name}', EMAIL = '{safe_email}', STATUS = '{safe_status}',
            UPDATED_AT = CURRENT_TIMESTAMP()
        WHERE SUPPLIER_ID = '{supplier_id}'
    """).collect()
    return True
