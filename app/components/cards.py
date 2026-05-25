"""
cards.py

Componente de cards informativos reutilizáveis.
Exibe blocos visuais com métricas, status de ciclo, indicadores de envio
e resumos de fornecedor na interface do portal.
"""

import streamlit as st


def metric_card(label: str, value: str, detail: str = "") -> str:
    """
    Retorna HTML de um card de métrica simples (fundo branco).
    Parâmetros:
        label  — texto do rótulo superior (uppercase automático pelo CSS)
        value  — valor principal em destaque
        detail — texto opcional abaixo do valor
    """
    detail_html = f'<p class="kmt-card-detail">{detail}</p>' if detail else ""
    return f"""
    <div class="kmt-card">
        <p class="kmt-card-label">{label}</p>
        <p class="kmt-card-value">{value}</p>
        {detail_html}
    </div>"""


def kpi_card(label: str, value: str) -> str:
    """
    Retorna HTML de um card KPI (variante admin com accent navy na borda inferior).
    Valor exibido em tamanho maior (24px).
    """
    return f"""
    <div class="kmt-card kmt-card--kpi">
        <p class="kmt-card-label">{label}</p>
        <p class="kmt-card-value">{value}</p>
    </div>"""


def navy_card(title: str, body: str, version: str = "") -> str:
    """
    Retorna HTML de um card com fundo navy (informativo/aviso).
    Parâmetros:
        title   — título com ícone de aviso
        body    — texto do aviso
        version — se fornecido, exibe bloco de versão no rodapé do card
    """
    version_block = ""
    if version:
        version_block = f"""
        <div class="kmt-navy-card-footer">
            <p class="kmt-navy-card-version-label">Versão do Sistema</p>
            <p class="kmt-navy-card-version">{version}</p>
        </div>"""
    return f"""
    <div class="kmt-card kmt-card--navy">
        <h4 class="kmt-navy-card-title">
            <span class="kmt-icon-yellow">⚠</span>&nbsp;{title}
        </h4>
        <p class="kmt-navy-card-body">{body}</p>
        {version_block}
    </div>"""


def render_cards_row(cards_html: list[str]) -> None:
    """
    Renderiza uma lista de cards HTML em colunas lado a lado.
    Parâmetro:
        cards_html — lista de strings HTML retornadas por metric_card / kpi_card
    """
    cols = st.columns(len(cards_html))
    for col, html in zip(cols, cards_html):
        with col:
            st.markdown(html, unsafe_allow_html=True)
