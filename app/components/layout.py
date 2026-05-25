"""
layout.py

Componente de layout base da aplicação.
Responsável por aplicar a identidade visual Komatsu (azul marinho, branco, amarelo,
cinza claro), configurar o cabeçalho com logo e renderizar o rodapé padrão.
"""

import streamlit as st
from pathlib import Path

_CSS_PATH = Path(__file__).parent.parent / "assets" / "style.css"


def load_css() -> None:
    """Lê style.css e injeta no app via st.markdown."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_header(
    title: str,
    user_name: str,
    user_email: str,
    user_initials: str,
) -> None:
    """
    Renderiza o topbar customizado com logo, título da página e avatar do usuário.
    Deve ser chamado antes de qualquer outro conteúdo no main.
    """
    st.markdown(
        f"""
        <div class="kmt-header">
            <div class="kmt-header-left">
                <span class="kmt-logo">KOMATSU</span>
                <div class="kmt-header-divider"></div>
                <span class="kmt-header-title">{title}</span>
            </div>
            <div class="kmt-header-right">
                <div class="kmt-header-user">
                    <span class="kmt-header-name">{user_name}</span>
                    <span class="kmt-header-email">{user_email}</span>
                </div>
                <div class="kmt-avatar">{user_initials}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Renderiza o rodapé padrão do portal."""
    st.markdown(
        """
        <div class="kmt-footer">
            <span>© 2024 Komatsu | Portal de Coleta e Validação | MVP v1.0</span>
            <span class="kmt-footer-links">
                <span>Privacidade</span>
                <span>Termos de Uso</span>
                <span>Suporte: TI Operações</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
