"""
validated_data.py

Tela de consulta de forecasts validados.
Exibe os forecasts válidos e ativos recebidos pelos fornecedores,
com filtros por período, fornecedor, filial e material.

Fontes de dados (prioridade):
1. Uploads válidos e ativos da sessão atual  → linha por upload (sem granularidade de material)
2. Dados de demonstração (mock)              → linha por material (granularidade completa)
3. Nenhum dado                               → estado vazio

Sem termos técnicos (sem TRUSTED, STAGING, RAW, camada simulada).
"""

import io

import pandas as pd
import streamlit as st

from components.badges import version_badge
from services.mock_data_service import get_mock_validated_forecast, get_current_open_window
from services.forecast_service import get_validated_forecasts_from_snowflake
from komatsu_ds import layout
from utils.constants import DEMO_MODE
from utils.dates import format_period_pt
from utils.logger import get_logger
from utils.session_state import get_session_validated_forecasts

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Labels dos filtros "selecionar todos" — explícitos para evitar ambiguidade
# ---------------------------------------------------------------------------

_ALL_PERIODS_LABEL   = "Todos os períodos"
_ALL_SUPPLIERS_LABEL = "Todos os fornecedores"
_ALL_BRANCHES_LABEL  = "Todas as filiais"
_ALL_MATERIALS_LABEL = "Todos os materiais"


# ---------------------------------------------------------------------------
# Normalização em formato unificado
# ---------------------------------------------------------------------------

def _session_to_rows() -> list[dict]:
    """
    Retorna as linhas normalizadas dos forecasts válidos da sessão.
    Uma linha por registro do arquivo (granularidade por material/filial/período).
    Fonte: session_validated_forecasts (populado em supplier_upload.py).
    """
    forecasts = get_session_validated_forecasts()
    rows = []
    for f in forecasts:
        qty = f.get("forecast_quantity")
        try:
            qty_val = int(qty) if qty is not None else 0
        except (TypeError, ValueError):
            qty_val = 0

        rows.append({
            "supplier":      f.get("supplier_name") or f.get("supplier_id") or "—",
            "branch":        f.get("branch") or "—",
            "material_code": f.get("material_code") or "—",
            "description":   f.get("material_description") or "—",
            "period":        format_period_pt(str(f.get("forecast_period") or "—")),
            "_period_key":   str(f.get("forecast_period") or "—"),
            "qty":           qty_val,
            "version":       int(f.get("upload_version") or 1),
            "processed_at":  str(f.get("uploaded_at") or "—"),
            "source_file":   f.get("source_file_name") or "—",
            "_source":       "session",
        })
    return rows


def _mock_to_rows() -> list[dict]:
    """Dados de demonstração como linhas da tabela (granularidade por material)."""
    rows = []
    for r in get_mock_validated_forecast():
        raw = r.get("period", "—")
        rows.append({**r, "_source": "mock", "_period_key": raw, "period": format_period_pt(raw)})
    return rows


# ---------------------------------------------------------------------------
# Seções da tela
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    layout.page_header(
        title="Forecasts Validados",
        subtitle="Consulte os forecasts válidos enviados pelos fornecedores.",
    )


def _render_demo_banner() -> None:
    st.markdown(
        '<div class="kmt-alert kmt-alert--info" style="margin-bottom:12px;">'
        '<div class="kmt-alert-icon">💡</div>'
        '<div>'
        '<p class="kmt-alert-title">Dados de demonstração</p>'
        '<p class="kmt-alert-body">'
        'Nenhum upload real foi realizado nesta sessão. '
        'Os dados abaixo são de demonstração e serão substituídos '
        'automaticamente após os fornecedores enviarem forecasts.'
        '</p></div></div>',
        unsafe_allow_html=True,
    )


def _render_session_note() -> None:
    """Nota exibida quando os dados vêm de uploads da sessão (nível de envio)."""
    st.markdown(
        '<p style="font-size:11px;color:#9CA3AF;margin:4px 0 8px 2px;">'
        'ℹ&nbsp;&nbsp;A quantidade prevista total representa a soma da coluna Qtd. dos forecasts válidos.'
        '</p>',
        unsafe_allow_html=True,
    )


def _render_filters(rows: list[dict]) -> tuple[list[dict], str, str]:
    """
    Filtros: Período, Fornecedor, Filial, Material.
    Opções de Filial e Material são construídas dinamicamente a partir dos dados.
    Retorna (linhas filtradas, período selecionado, fornecedor selecionado).

    Default de Período: janela de coleta ativa (se existir e o período estiver nos dados).
    Fallback: _ALL_PERIODS_LABEL (todos os períodos).
    """
    # Períodos ordenados cronologicamente (desc) usando chave raw, exibindo formatado
    period_map = {r["_period_key"]: r["period"] for r in rows}
    periods    = [period_map[k] for k in sorted(period_map.keys(), reverse=True)]
    suppliers = sorted({r["supplier"]      for r in rows})
    branches  = sorted({r["branch"]        for r in rows if r["branch"]        != "—"})
    materials = sorted({r["material_code"] for r in rows if r["material_code"] != "—"})

    # --- Default de período: janela ativa, senão "todos" ---
    period_opts = [_ALL_PERIODS_LABEL] + periods
    window = get_current_open_window()
    active_period_raw = window.get("period") if window else None
    active_period_fmt = format_period_pt(active_period_raw) if active_period_raw else None

    if active_period_fmt and active_period_fmt in periods:
        default_period_index = period_opts.index(active_period_fmt)
    else:
        default_period_index = 0  # fallback: "Todos os períodos"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sel_period = st.selectbox(
            "Período",
            period_opts,
            index=default_period_index,
            key="vd_filter_period",
        )
    with col2:
        sel_supplier = st.selectbox(
            "Fornecedor",
            [_ALL_SUPPLIERS_LABEL] + suppliers,
            key="vd_filter_supplier",
        )
    with col3:
        branch_opts = [_ALL_BRANCHES_LABEL] + branches
        sel_branch  = st.selectbox(
            "Filial",
            branch_opts,
            key="vd_filter_branch",
            help="Disponível quando há dados com granularidade por filial." if not branches else None,
        )
    with col4:
        material_opts = [_ALL_MATERIALS_LABEL] + materials
        sel_material  = st.selectbox(
            "Material",
            material_opts,
            key="vd_filter_material",
            help="Disponível quando há dados com granularidade por material." if not materials else None,
        )

    # Aplicar filtros
    result = rows

    if sel_period != _ALL_PERIODS_LABEL:
        result = [r for r in result if r["period"] == sel_period]

    if sel_supplier != _ALL_SUPPLIERS_LABEL:
        result = [r for r in result if r["supplier"] == sel_supplier]

    if sel_branch != _ALL_BRANCHES_LABEL and branches:
        result = [r for r in result if r["branch"] == sel_branch]

    if sel_material != _ALL_MATERIALS_LABEL and materials:
        result = [r for r in result if r["material_code"] == sel_material]

    return result, sel_period, sel_supplier


def _render_summary_cards(
    rows: list[dict],
    sel_period: str,
    sel_supplier: str,
    demo_mode: bool,
) -> None:
    """
    4 cards base + "Versão Ativa" condicional (só quando fornecedor+período específicos).

    Regra:
    - "Qtd. Prevista Total" → soma de qty (mock) ou linhas válidas (sessão)
    - "Versão Ativa" → só exibido quando fornecedor E período estão filtrados
    """
    total         = len(rows)
    n_suppliers   = len({r["supplier"] for r in rows})
    qty_total     = sum(r["qty"] for r in rows if isinstance(r["qty"], int))
    # sel_period já é o label correto: "Maio/2026" ou "Todos os períodos"
    period_label  = sel_period

    qty_card_label = "Qtd. Prevista Total"

    cards = [
        {"label": "Registros Validados", "value": str(total),                           "icon": "✅", "neutral": True},
        {"label": "Fornecedores",        "value": str(n_suppliers),                     "icon": "🏢", "neutral": True},
        {"label": "Período",             "value": period_label,                         "icon": "📅", "neutral": True},
        {"label": qty_card_label,        "value": str(qty_total) if qty_total else "—", "icon": "📦", "neutral": True},
    ]

    # "Versão Ativa" apenas quando há fornecedor E período específicos selecionados
    if sel_supplier != _ALL_SUPPLIERS_LABEL and sel_period != _ALL_PERIODS_LABEL and rows:
        versions = [r["version"] for r in rows if isinstance(r["version"], int)]
        if versions:
            cards.append({"label": "Versão Ativa", "value": f"v.{max(versions)}", "icon": "🔖", "neutral": True})

    layout.kpi_row(cards)


def _render_table(rows: list[dict]) -> str:
    """
    HTML da tabela de forecasts validados.
    Colunas: Fornecedor, Filial, Cód. Material, Descrição,
             Período, Qtd., Versão, Data de Envio, Arquivo.
    """
    if not rows:
        return ""

    table_rows = ""
    for r in rows:
        ver = version_badge(r["version"]) if isinstance(r["version"], int) else r["version"]

        table_rows += (
            '<tr class="kmt-table-row">'
            f'<td class="kmt-table-cell" style="font-weight:700;color:#002B5C;">{r["supplier"]}</td>'
            f'<td class="kmt-table-cell" style="color:#374151;">{r["branch"]}</td>'
            f'<td class="kmt-table-cell" style="font-family:monospace;font-size:11px;color:#6B7280;">{r["material_code"]}</td>'
            f'<td class="kmt-table-cell" style="color:#374151;font-size:12px;">{r["description"]}</td>'
            f'<td class="kmt-table-cell" style="color:#2563EB;font-weight:700;">{r["period"]}</td>'
            f'<td class="kmt-table-cell kmt-td-center" style="font-weight:700;color:#15803D;">{r["qty"]}</td>'
            f'<td class="kmt-table-cell kmt-td-center">{ver}</td>'
            f'<td class="kmt-table-cell kmt-td-date">{r["processed_at"]}</td>'
            f'<td class="kmt-table-cell" style="font-size:11px;font-family:monospace;color:#6B7280;'
            f'max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" '
            f'title="{r["source_file"]}">{r["source_file"]}</td>'
            '</tr>'
        )

    return (
        '<div class="kmt-table-container">'
        '<div class="kmt-table-header">'
        '<span class="kmt-table-title">Forecasts Validados</span>'
        f'<span style="font-size:11px;color:#9CA3AF;">{len(rows)} registro(s)</span>'
        '</div>'
        '<div class="kmt-table-scroll">'
        '<table class="kmt-table">'
        '<thead><tr class="kmt-thead-row">'
        '<th class="kmt-th">Fornecedor</th>'
        '<th class="kmt-th">Filial</th>'
        '<th class="kmt-th">Cód. Material</th>'
        '<th class="kmt-th">Descrição</th>'
        '<th class="kmt-th">Período</th>'
        '<th class="kmt-th kmt-th-center">Qtd.</th>'
        '<th class="kmt-th kmt-th-center">Versão</th>'
        '<th class="kmt-th">Data de Envio</th>'
        '<th class="kmt-th">Arquivo</th>'
        '</tr></thead>'
        f'<tbody>{table_rows}</tbody>'
        '</table></div></div>'
    )


def _render_export(rows: list[dict]) -> None:
    """
    Botões de exportação: XLSX primeiro, CSV segundo.
    XLSX: via openpyxl (disabled se ausente).
    CSV:  sempre disponível.
    """
    col_names = [
        "Fornecedor", "Filial", "Cód. Material", "Descrição",
        "Período", "Qtd.", "Versão", "Data de Envio", "Arquivo",
    ]
    df = pd.DataFrame(
        [{
            "Fornecedor":    r["supplier"],
            "Filial":        r["branch"],
            "Cód. Material": r["material_code"],
            "Descrição":     r["description"],
            "Período":       r["period"],
            "Qtd.":          r["qty"],
            "Versão":        r["version"],
            "Data de Envio": r["processed_at"],
            "Arquivo":       r["source_file"],
        } for r in rows]
    )
    empty = len(rows) == 0

    col_xlsx, col_csv, _ = st.columns([2, 2, 4])

    with col_xlsx:
        try:
            import openpyxl  # noqa: F401
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Forecasts Validados")
            st.download_button(
                label="⬇  Exportar XLSX",
                data=buf.getvalue(),
                file_name="forecasts_validados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=empty,
            )
        except ImportError:
            st.download_button(
                label="⬇  Exportar XLSX",
                data=b"",
                file_name="forecasts_validados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=True,
                help="Instale openpyxl para habilitar a exportação XLSX.",
            )

    with col_csv:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇  Exportar CSV",
            data=csv_bytes,
            file_name="forecasts_validados.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=empty,
        )


def _render_empty_state() -> None:
    layout.empty_state(
        message=(
            "Nenhum forecast válido disponível para os filtros selecionados. "
            "Ajuste os filtros ou aguarde o envio dos fornecedores."
        ),
        icon="📭",
    )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """
    Renderiza a tela de forecasts validados.
    Chamado por streamlit_app.py quando page == 'validated_data'.

    Fluxo:
    1. Obtém dados (sessão → mock como demo → vazio)
    2. Mostra banner de demonstração se necessário
    3. Aplica filtros
    4. Renderiza cards, exportação e tabela
    """
    try:
        _render_impl()
    except Exception as exc:
        _logger.exception("Erro ao renderizar Forecasts Validados: %s", exc)
        st.error("Não foi possível carregar estas informações no momento. Tente novamente em alguns instantes.")


def _render_impl() -> None:
    """Implementação interna da tela de forecasts validados."""
    _render_page_header()

    # --- Fonte de dados (prioridade: Snowflake → sessão → mock) ---
    demo_mode = False

    # 1. Fonte de verdade: Snowflake TRUSTED.FORECAST_VALIDATED
    sf_rows = get_validated_forecasts_from_snowflake()
    if sf_rows:
        _logger.info(
            "validated_data: %d registros carregados do Snowflake.", len(sf_rows),
        )
        base_rows = sf_rows
    else:
        # 2. Fallback: session_state (uploads da sessão atual)
        session_rows = _session_to_rows()
        if session_rows:
            _logger.warning(
                "validated_data: fallback para session_state — %d registros. "
                "Snowflake não retornou dados.", len(session_rows),
            )
            base_rows = session_rows
        elif DEMO_MODE:
            # 3. Fallback: dados de demonstração
            mock_rows = _mock_to_rows()
            if mock_rows:
                base_rows = mock_rows
                demo_mode = True
            else:
                base_rows = []
        else:
            # Nenhuma fonte disponível
            _logger.info("validated_data: nenhum dado encontrado em nenhuma fonte.")
            base_rows = []

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    # Banner de demonstração
    if demo_mode:
        _render_demo_banner()

    # Sem dados em nenhuma fonte → empty state e encerra
    if not base_rows:
        layout.kpi_row([
            {"label": "Registros Validados",  "value": "0", "icon": "✅", "neutral": True},
            {"label": "Fornecedores",         "value": "0", "icon": "🏢", "neutral": True},
            {"label": "Período",              "value": "—", "icon": "📅", "neutral": True},
            {"label": "Qtd. Prevista Total",  "value": "—", "icon": "📦", "neutral": True},
        ])
        _render_empty_state()
        return

    # --- Filtros ---
    filtered, sel_period, sel_supplier = _render_filters(base_rows)

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    # --- Cards ---
    _render_summary_cards(filtered, sel_period, sel_supplier, demo_mode)

    # --- Vazio pós-filtro ---
    if not filtered:
        _render_empty_state()
        return

    # Nota de contexto (apenas quando fallback de sessão é usado)
    if base_rows and base_rows[0].get("_source") == "session":
        _render_session_note()

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    # --- Exportação ---
    _render_export(filtered)

    # --- Tabela ---
    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown(_render_table(filtered), unsafe_allow_html=True)
