"""
navigation.py

Componente de navegação lateral (sidebar).
Monta o menu de navegação de acordo com o perfil do usuário logado
(fornecedor ou admin), controlando quais páginas são visíveis.
"""

import streamlit as st

from utils.session_state import clear_selection
from utils.streamlit_compat import safe_rerun

# Menus por perfil
_SUPPLIER_MENU = [
    {"icon": "🏠", "label": "Dashboard",        "page": "home"},
    {"icon": "📤", "label": "Enviar Arquivo",   "page": "upload"},
    {"icon": "📋", "label": "Meus Envios",      "page": "history"},
]

_ADMIN_MENU = [
    {"icon": "📊", "label": "Painel de Coleta",    "page": "admin_dashboard"},
    {"icon": "📅", "label": "Janelas de Envio",   "page": "admin_windows"},
    {"icon": "📦", "label": "Estoques Validados", "page": "stock_validated"},
    {"icon": "✅", "label": "Forecasts Validados", "page": "validated_data"},
    {"icon": "🏭", "label": "Fornecedores",        "page": "admin_suppliers"},
]


def render_sidebar(role: str, current_page: str) -> None:
    """
    Renderiza a sidebar completa: menu por perfil, widget de janela e logout.
    Deve ser chamado dentro de `with st.sidebar:`.
    A marca KOMATSU é exibida apenas no header principal da página (render_header).
    """
    # --- Label de seção ---
    section_label = "Fornecedor" if role == "supplier" else "Administrativo"
    st.markdown(
        f'<div class="kmt-sidebar-section-label">{section_label}</div>',
        unsafe_allow_html=True,
    )

    # --- Itens de menu ---
    menu = _SUPPLIER_MENU if role == "supplier" else _ADMIN_MENU

    for item in menu:
        is_active = current_page == item["page"]
        container_class = "kmt-nav-active" if is_active else ""

        st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
        if st.button(
            f"{item['icon']}  {item['label']}",
            key=f"nav_{item['page']}",
            use_container_width=True,
        ):
            st.session_state.page = item["page"]
            safe_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # --- Widget janela do ciclo (dinâmico — sem dados hardcoded) ---
    from services.mock_data_service import get_current_open_window
    window = get_current_open_window()
    if window:
        label      = window.get("label", "")
        closes_at  = window.get("closes_at") or window.get("end_date", "")
        start_date = window.get("start_date", "")
        pct        = int(window.get("progress_pct", 0))
        if start_date and closes_at and closes_at != "—":
            detail = f'{pct}%&nbsp;·&nbsp;<em>{start_date} a {closes_at}</em>'
        elif closes_at and closes_at != "—":
            detail = f'{pct}%&nbsp;·&nbsp;<em>Encerra em {closes_at}</em>'
        else:
            detail = label
        st.markdown(
            '<div class="kmt-sidebar-window">'
            f'<div class="kmt-sidebar-window-label">Janela — {label}</div>'
            '<div class="kmt-sidebar-progress">'
            f'<div class="kmt-sidebar-progress-bar" style="width:{pct}%"></div>'
            '</div>'
            f'<div class="kmt-sidebar-window-detail">{detail}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="kmt-sidebar-divider"></div>', unsafe_allow_html=True)

    # --- Botão sair ---
    st.markdown('<div class="kmt-nav-logout">', unsafe_allow_html=True)
    if st.button("🚪  Sair do Portal", key="nav_logout", use_container_width=True):
        # Limpa seleções e contextos de navegação
        clear_selection()
        # Limpa a sessão e retorna para login
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.page = "home"
        st.session_state.user_name = ""
        st.session_state.user_email = ""
        st.session_state.user_initials = ""
        safe_rerun()
    st.markdown("</div>", unsafe_allow_html=True)
