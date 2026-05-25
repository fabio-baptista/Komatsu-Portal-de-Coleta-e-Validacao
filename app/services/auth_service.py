"""
auth_service.py

Serviço de autenticação e controle de sessão — Portal Komatsu.

STATUS ATUAL: Stub / MVP local
-----------------------------------------------------------------------
A autenticação neste MVP é simulada. O login é feito por botão de perfil
(Fornecedor / Administrador) sem credenciais reais. Os dados do usuário
ativo são carregados de mock_data_service.get_current_mock_user().

Este arquivo está reservado para a implementação da autenticação real,
que será definida na integração com Snowflake/IdP ou mecanismo aprovado
pelo cliente.

Evolução esperada:
- Substituir _do_login (streamlit_app.py) por autenticação via SSO/IdP.
- Implementar get_current_user() consultando o sistema de identidade real.
- Implementar is_admin() / is_supplier() a partir de claims do token.
- Registrar audit log de acesso por usuário.
-----------------------------------------------------------------------
"""

import streamlit as st


# ---------------------------------------------------------------------------
# Funções stub — retornam dados do session_state atual (MVP local)
# ---------------------------------------------------------------------------

def get_current_role() -> str | None:
    """
    Retorna o perfil do usuário logado ('supplier' | 'admin') ou None.

    No MVP, o perfil é definido no login simulado e armazenado em
    st.session_state.role. Em produção, virá de claims do token de autenticação.
    """
    return st.session_state.get("role")


def get_current_user() -> dict:
    """
    Retorna um dicionário com os dados básicos do usuário logado.

    No MVP, os dados vêm do session_state preenchido pelo mock de login.
    Em produção, virá do sistema de identidade (SSO/IdP/Snowflake).

    Retorno:
        {
            "name":        str,
            "email":       str,
            "role":        str | None,
            "supplier_id": str | None,
        }
    """
    return {
        "name":        st.session_state.get("user_name", ""),
        "email":       st.session_state.get("user_email", ""),
        "role":        st.session_state.get("role"),
        "supplier_id": st.session_state.get("supplier_id"),
    }


def is_admin() -> bool:
    """
    Retorna True se o usuário logado tem perfil administrativo.

    No MVP, verifica st.session_state.role.
    Em produção, verificará claims do token.
    """
    return st.session_state.get("role") == "admin"


def is_supplier() -> bool:
    """
    Retorna True se o usuário logado tem perfil de fornecedor.

    No MVP, verifica st.session_state.role.
    Em produção, verificará claims do token.
    """
    return st.session_state.get("role") == "supplier"


def is_authenticated() -> bool:
    """
    Retorna True se há uma sessão ativa (usuário logado).

    No MVP, verifica st.session_state.logged_in.
    Em produção, validará o token de sessão.
    """
    return bool(st.session_state.get("logged_in"))
