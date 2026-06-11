"""
stock_validated.py

Tela de consulta de estoques validados (TRUSTED.STOCK_VALIDATED).
Visao admin — permite visualizar dados de estoque enviados pelos fornecedores.
"""

import streamlit as st
import pandas as pd

from utils.logger import get_logger
from utils.streamlit_compat import safe_rerun

_logger = get_logger(__name__)

_DATABASE = "KBI_DATA_JOURNEY_DEV_DB"


# ---------------------------------------------------------------------------
# Leitura de dados
# ---------------------------------------------------------------------------

def _get_stock_data() -> pd.DataFrame:
    """Busca dados ativos de TRUSTED.STOCK_VALIDATED."""
    try:
        from services.snowflake_service import get_snowflake_session
        session = get_snowflake_session()
        if session is None:
            return pd.DataFrame()

        query = f"""
            SELECT SUPPLIER_NAME, BRANCH, MATERIAL_CODE, MATERIAL_DESCRIPTION,
                   STOCK_QUANTITY, UNIT_COST, TOTAL_COST,
                   PURCHASE_DATE, LAST_SALE_DATE, INVOICE_NUMBER,
                   STOCK_YEAR, STOCK_MONTH,
                   UPLOAD_VERSION, UPLOADED_AT, SOURCE_FILE_NAME
            FROM {_DATABASE}.TRUSTED.STOCK_VALIDATED
            WHERE IS_ACTIVE = TRUE
            ORDER BY UPLOADED_AT DESC
        """
        df = session.sql(query).to_pandas()
        return df if df is not None else pd.DataFrame()

    except Exception as exc:
        _logger.exception("Erro ao buscar estoques validados: %s", exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        '<div class="kmt-section">'
        '<p class="kmt-section-title">Estoques Validados</p>'
        '<p class="kmt-section-subtitle">'
        'Consulte os dados de estoque validados enviados pelos distribuidores.'
        '</p></div>',
        unsafe_allow_html=True,
    )


def _render_table(df: pd.DataFrame) -> None:
    """Renderiza tabela de estoques validados."""
    if df.empty:
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-top:12px;">'
            '<div class="kmt-alert-icon">&#128237;</div>'
            '<div>'
            '<p class="kmt-alert-title">Nenhum estoque validado disponivel.</p>'
            '<p class="kmt-alert-body">'
            'Os dados aparecerão aqui após os distribuidores enviarem relatórios de estoque.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
        return

    from components.cards import metric_card, render_cards_row

    # KPIs
    n_records = len(df)
    n_suppliers = df["SUPPLIER_NAME"].nunique() if "SUPPLIER_NAME" in df.columns else 0
    total_qty = df["STOCK_QUANTITY"].sum() if "STOCK_QUANTITY" in df.columns else 0
    total_cost = df["TOTAL_COST"].sum() if "TOTAL_COST" in df.columns else 0

    render_cards_row([
        metric_card("Registros", str(n_records)),
        metric_card("Distribuidores", str(n_suppliers)),
        metric_card("Qtd Total", f"{total_qty:,.0f}"),
        metric_card("Custo Total", f"R$ {total_cost:,.2f}"),
    ])

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        suppliers = sorted(df["SUPPLIER_NAME"].dropna().unique().tolist()) if "SUPPLIER_NAME" in df.columns else []
        sel_sup = st.multiselect("Distribuidor", options=suppliers, key="stock_flt_sup")
    with col2:
        branches = sorted(df["BRANCH"].dropna().unique().tolist()) if "BRANCH" in df.columns else []
        sel_branch = st.multiselect("Filial", options=branches, key="stock_flt_branch")
    with col3:
        materials = sorted(df["MATERIAL_CODE"].dropna().unique().tolist()) if "MATERIAL_CODE" in df.columns else []
        sel_mat = st.multiselect("Material", options=materials, key="stock_flt_mat")

    filtered = df.copy()
    if sel_sup:
        filtered = filtered[filtered["SUPPLIER_NAME"].isin(sel_sup)]
    if sel_branch:
        filtered = filtered[filtered["BRANCH"].isin(sel_branch)]
    if sel_mat:
        filtered = filtered[filtered["MATERIAL_CODE"].isin(sel_mat)]

    # Tabela HTML
    display_cols = [
        ("SUPPLIER_NAME", "Distribuidor"),
        ("BRANCH", "Filial"),
        ("MATERIAL_CODE", "Material"),
        ("MATERIAL_DESCRIPTION", "Descricao"),
        ("STOCK_QUANTITY", "Qtd"),
        ("UNIT_COST", "Custo Unit"),
        ("TOTAL_COST", "Custo Total"),
        ("PURCHASE_DATE", "Data Compra"),
        ("SOURCE_FILE_NAME", "Arquivo"),
    ]

    header_html = "".join(f'<th class="kmt-th">{lbl}</th>' for _, lbl in display_cols)
    rows_html = ""
    for _, row in filtered.head(500).iterrows():
        cells = ""
        for col_name, _ in display_cols:
            val = row.get(col_name, "")
            if pd.isna(val):
                val = ""
            elif col_name in ("STOCK_QUANTITY", "UNIT_COST", "TOTAL_COST"):
                try:
                    val = f"{float(val):,.2f}"
                except (ValueError, TypeError):
                    val = str(val)
            else:
                val = str(val)
            cells += f'<td class="kmt-table-cell">{val}</td>'
        rows_html += f'<tr class="kmt-table-row">{cells}</tr>'

    st.markdown(
        '<div class="kmt-table-container">'
        '<div class="kmt-table-header">'
        f'<span class="kmt-table-title">Estoques Validados</span>'
        f'<span style="font-size:11px;color:#9CA3AF;">{len(filtered)} registro(s)</span>'
        '</div>'
        '<div class="kmt-table-scroll">'
        '<table class="kmt-table">'
        f'<thead><tr class="kmt-thead-row">{header_html}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """Renderiza a tela de Estoques Validados."""
    try:
        _render_page_header()
        df = _get_stock_data()
        _render_table(df)
    except Exception as exc:
        _logger.exception("Erro ao renderizar Estoques Validados: %s", exc)
        st.error("Não foi possível carregar estas informações no momento. Tente novamente.")
