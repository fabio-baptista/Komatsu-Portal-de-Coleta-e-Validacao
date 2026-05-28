"""
streamlit_compat.py

Helper de compatibilidade entre versões do Streamlit.
Garante funcionamento tanto localmente (Streamlit >= 1.27 com st.rerun())
quanto no Streamlit in Snowflake (versão mais antiga que usa st.experimental_rerun()).
"""

import streamlit as st


def safe_rerun() -> None:
    """
    Executa rerun do app de forma compatível com diferentes versões do Streamlit.

    Ordem de tentativa:
      1. st.rerun()              — Streamlit >= 1.27 (padrão local)
      2. st.experimental_rerun() — Streamlit < 1.27 (SiS e versões anteriores)
      3. Fallback com aviso       — caso nenhum dos dois exista
    """
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.warning("Ação concluída. Atualize a página para ver as alterações.")
