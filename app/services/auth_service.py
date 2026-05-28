"""
auth_service.py

Servico de autenticacao - Portal Komatsu.
Autentica usuarios via CONTROL.USERS com SHA2-256 + salt.
"""

import streamlit as st
from typing import Optional

from services.snowflake_service import execute_query, get_snowflake_session

DATABASE = "KBI_DATA_JOURNEY_DEV_DB"
SALT_PREFIX = "salt_kmt_"
SALT_SUFFIX = "_portal"


def _hash_password(password: str) -> str:
    session = get_snowflake_session()
    if session is None:
        return ""
    result = session.sql(
        f"SELECT SHA2('{SALT_PREFIX}' || '{password}' || '{SALT_SUFFIX}', 256) as H"
    ).collect()
    return result[0]["H"] if result else ""


def authenticate_user(email: str, password: str) -> Optional[dict]:
    password_hash = _hash_password(password)
    if not password_hash:
        return None

    df = execute_query(
        f"""SELECT u.USER_ID, u.EMAIL, u.DISPLAY_NAME, u.ROLE, u.SUPPLIER_ID, u.IS_ACTIVE,
                   s.SUPPLIER_CODE, s.SUPPLIER_NAME, s.STATUS as SUPPLIER_STATUS
            FROM {DATABASE}.CONTROL.USERS u
            LEFT JOIN {DATABASE}.CONTROL.SUPPLIERS s ON u.SUPPLIER_ID = s.SUPPLIER_ID
            WHERE LOWER(u.EMAIL) = :email AND u.PASSWORD_HASH = :hash""",
        params={"email": email.strip().lower(), "hash": password_hash},
    )

    if df is None or df.empty:
        return None

    row = df.iloc[0].to_dict()

    if not row.get("IS_ACTIVE", False):
        return None

    return {
        "user_id": row["USER_ID"],
        "email": row["EMAIL"],
        "display_name": row["DISPLAY_NAME"],
        "role": row["ROLE"],
        "supplier_id": row.get("SUPPLIER_ID"),
        "supplier_code": row.get("SUPPLIER_CODE"),
        "supplier_name": row.get("SUPPLIER_NAME"),
        "supplier_status": row.get("SUPPLIER_STATUS"),
    }


def authenticate_supplier_by_email(email: str) -> Optional[dict]:
    df = execute_query(
        f"""SELECT u.USER_ID, u.EMAIL, u.DISPLAY_NAME, u.ROLE, u.SUPPLIER_ID, u.IS_ACTIVE,
                   s.SUPPLIER_CODE, s.SUPPLIER_NAME, s.STATUS as SUPPLIER_STATUS
            FROM {DATABASE}.CONTROL.USERS u
            JOIN {DATABASE}.CONTROL.SUPPLIERS s ON u.SUPPLIER_ID = s.SUPPLIER_ID
            WHERE LOWER(u.EMAIL) = :email AND u.ROLE = 'supplier'""",
        params={"email": email.strip().lower()},
    )

    if df is None or df.empty:
        return None

    row = df.iloc[0].to_dict()

    return {
        "user_id": row["USER_ID"],
        "email": row["EMAIL"],
        "display_name": row["DISPLAY_NAME"],
        "role": row["ROLE"],
        "supplier_id": row.get("SUPPLIER_ID"),
        "supplier_code": row.get("SUPPLIER_CODE"),
        "supplier_name": row.get("SUPPLIER_NAME"),
        "supplier_status": row.get("SUPPLIER_STATUS"),
        "is_active": row.get("IS_ACTIVE", False),
    }


def do_supplier_login(email: str) -> dict:
    user = authenticate_supplier_by_email(email)
    if user is None:
        return {"success": False, "error": "email_not_found"}

    if not user.get("is_active", False):
        return {"success": False, "error": "user_inactive"}

    if user.get("supplier_status") != "active":
        return {"success": False, "error": "supplier_inactive"}

    st.session_state.logged_in = True
    st.session_state.role = "supplier"
    st.session_state.user_name = user["supplier_name"] or user["display_name"]
    st.session_state.user_email = user["email"]
    st.session_state.user_initials = _initials(user["supplier_name"] or user["display_name"])
    st.session_state.supplier_id = user["supplier_code"]
    st.session_state.supplier_email = user["email"]
    st.session_state.user_id = user["user_id"]
    st.session_state.page = "home"

    return {"success": True}


def do_admin_login(email: str = "admin@komatsu.com.br", password: str = "") -> dict:
    if not password:
        df = execute_query(
            f"""SELECT u.USER_ID, u.EMAIL, u.DISPLAY_NAME, u.ROLE
                FROM {DATABASE}.CONTROL.USERS u
                WHERE LOWER(u.EMAIL) = :email AND u.ROLE = 'admin' AND u.IS_ACTIVE = TRUE""",
            params={"email": email.strip().lower()},
        )
        if df is None or df.empty:
            return {"success": False, "error": "admin_not_found"}
        row = df.iloc[0].to_dict()
    else:
        user = authenticate_user(email, password)
        if user is None:
            return {"success": False, "error": "invalid_credentials"}
        if user["role"] != "admin":
            return {"success": False, "error": "not_admin"}
        row = user

    st.session_state.logged_in = True
    st.session_state.role = "admin"
    st.session_state.user_name = row.get("display_name") or row.get("DISPLAY_NAME", "Admin")
    st.session_state.user_email = row.get("email") or row.get("EMAIL", "")
    st.session_state.user_initials = _initials(row.get("display_name") or row.get("DISPLAY_NAME", "Admin"))
    st.session_state.user_id = row.get("user_id") or row.get("USER_ID", "")
    st.session_state.page = "admin_dashboard"

    return {"success": True}


def _initials(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "??"
