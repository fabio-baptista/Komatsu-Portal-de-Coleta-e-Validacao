"""
admin_dashboard.py

Painel de Coleta de Forecast — visão admin.
Exibe KPIs de participação por período, filtros de período/fornecedor/status
e tabela consolidada de status por fornecedor.

Dados: dinâmicos, via get_admin_status_rows(period) e get_all_uploads().
"""

import streamlit as st

from components.badges import status_badge, version_badge
from components.cards import kpi_card, render_cards_row
from services.mock_data_service import get_current_open_window
from services.supplier_service import get_all_suppliers
from services.upload_service import get_admin_status_rows, get_all_uploads, get_canceled_uploads_count, get_available_periods_from_snowflake
from utils.constants import get_enabled_report_types
from utils.session_state import navigate_to
from utils.streamlit_compat import safe_rerun


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_STATUS_PT: dict[str, str] = {
    "recebido":           "Recebido",
    "pending":            "Pendente",
    "cancelled_pending":  "Cancelado/Pendente",
}
_PT_TO_STATUS: dict[str, str] = {v: k for k, v in _STATUS_PT.items()}

_MONTHS = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _period_label(period: str) -> str:
    """Converte '2026-05' em 'Maio/2026'. Retorna o próprio valor em caso de erro."""
    try:
        year, month = period.split("-")
        return f"{_MONTHS[int(month) - 1]}/{year}"
    except Exception:
        return period


def _get_available_periods() -> list[str]:
    """
    Retorna todos os períodos presentes nos uploads, ordenados
    do mais recente ao mais antigo, normalizados para YYYY-MM.
    Garante que o período aberto atual sempre figure na lista.
    Prioridade: Snowflake → fallback session/mock.
    """
    from utils.dates import to_period_ym

    # 1. Tentar Snowflake
    sf_periods = get_available_periods_from_snowflake()
    if sf_periods:
        periods = sorted([p for p in sf_periods if p], reverse=True)
    else:
        # 2. Fallback: session/mock
        all_ups = get_all_uploads(include_mock=True)
        normalized = {to_period_ym(u.period) for u in all_ups}
        periods = sorted([p for p in normalized if p], reverse=True)

    window = get_current_open_window()
    if window and window["period"] and window["period"] not in periods:
        periods.insert(0, window["period"])

    return periods or [""]


def _apply_filters(
    rows: list[dict],
    suppliers: list[str],
    statuses: list[str],
) -> list[dict]:
    """Filtra linhas da tabela por fornecedor e/ou status."""
    result = rows
    if suppliers:
        result = [r for r in result if r["name"] in suppliers]
    if statuses:
        internal = {_PT_TO_STATUS.get(s, s.lower()) for s in statuses}
        result = [r for r in result if r["status"] in internal]
    return result


# ---------------------------------------------------------------------------
# Seções da tela
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        '<div class="kmt-section">'
        '<p class="kmt-section-title">Painel de Coleta de Forecast</p>'
        '<p class="kmt-section-subtitle">'
        'Acompanhamento do ciclo de envio de forecast por fornecedor. '
        'Utilize os filtros abaixo para selecionar período e fornecedores.'
        '</p></div>',
        unsafe_allow_html=True,
    )


def _render_filters(periods: list[str]) -> tuple[str, list[str], list[str]]:
    """
    Renderiza os filtros de período, fornecedor e status.
    Retorna (selected_period, selected_suppliers, selected_statuses).
    """
    # Construir opções de período com labels legíveis
    period_options = [(p, _period_label(p)) for p in periods]
    period_labels  = [lbl for _, lbl in period_options]

    # Índice padrão = período aberto atual
    window         = get_current_open_window()
    default_period = window["period"] if window else (periods[0] if periods else "")
    default_index  = next(
        (i for i, (p, _) in enumerate(period_options) if p == default_period),
        0,
    )

    # Nomes dos fornecedores ativos para o multiselect — apenas da sessão (DEMO_MODE=False)
    supplier_names = [s.name for s in get_all_suppliers() if s.status == "active"]

    status_options = list(_STATUS_PT.values())  # labels PT

    col1, col2, col3 = st.columns([2, 3, 3])

    with col1:
        selected_label = st.selectbox(
            "Período",
            options=period_labels,
            index=default_index,
            key="adm_filter_period",
        )
        selected_period = next(
            (p for p, lbl in period_options if lbl == selected_label),
            default_period,
        )

    with col2:
        selected_suppliers = st.multiselect(
            "Todos os fornecedores",
            options=supplier_names,
            default=[],
            key="adm_filter_supplier",
        )

    with col3:
        selected_statuses = st.multiselect(
            "Todos os status",
            options=status_options,
            default=[],
            key="adm_filter_status",
        )

    return selected_period, selected_suppliers, selected_statuses


def _render_kpi_cards(rows: list[dict], period_lbl: str, canceled_count: int = 0) -> None:
    """
    4 cards KPI orientados a coleta.

    Status da coleta (nao do fornecedor, nao do arquivo):
      Participantes          = fornecedores ativos com coleta habilitada
      Recebidos              = com envio valido atual no periodo
      Pendentes              = sem envio valido atual (inclui cancelled_pending)
      Cancelamentos no Periodo = eventos de cancelamento no periodo
    """
    participantes = len(rows)
    recebidos = sum(1 for r in rows if r["status"] == "recebido")
    pendentes = participantes - recebidos

    render_cards_row([
        kpi_card("Participantes",             str(participantes)),
        kpi_card("Recebidos",                 str(recebidos)),
        kpi_card("Pendentes",                 str(pendentes)),
        kpi_card("Cancelamentos no Periodo",  str(canceled_count)),
    ])

    if pendentes > 0:
        st.markdown(
            f'<p style="font-size:12px;color:#B45309;font-weight:600;margin:6px 0 0 2px;">'
            f'&#9888;&nbsp;&nbsp;{pendentes} fornecedor(es) sem envio valido no periodo.</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<p style="font-size:12px;color:#15803D;font-weight:600;margin:6px 0 0 2px;">'
            f'&#10003;&nbsp;&nbsp;Todos os {participantes} fornecedores '
            f'entregaram envio valido no periodo.</p>',
            unsafe_allow_html=True,
        )

    if canceled_count > 0:
        st.markdown(
            f'<p style="font-size:11px;color:#6B7280;margin:3px 0 0 2px;">'
            f'&#8505;&nbsp;&nbsp;{canceled_count} cancelamento(s) no periodo.</p>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<p style="font-size:11px;color:#9CA3AF;margin:4px 0 12px 2px;">'
        f'Periodo: <strong style="color:#6B7280;">{period_lbl}</strong>'
        f'&nbsp;&middot;&nbsp;'
        f'<strong>Participantes</strong> = fornecedores ativos'
        f'&nbsp;&middot;&nbsp;'
        f'<strong>Recebidos</strong> = com envio valido atual'
        f'&nbsp;&middot;&nbsp;'
        f'<strong>Pendentes</strong> = sem envio valido atual'
        f'&nbsp;&middot;&nbsp;'
        f'<strong>Cancelamentos</strong> = eventos de cancelamento no periodo.</p>',
        unsafe_allow_html=True,
    )


# Proporcoes das colunas da tabela admin (6 dados + acoes)
_ADM_COLS = [2.5, 1.2, 1.2, 1.3, 1.5, 0.8, 0.7]


def _cb_adm_ver_detalhe(upload_id: str) -> None:
    navigate_to("admin_upload_detail", upload_id=upload_id, origin="admin_dashboard")


def _cb_adm_ver_erros(upload_id: str) -> None:
    navigate_to("errors", upload_id=upload_id, origin="admin_dashboard")


def _render_status_table(rows: list[dict], period_lbl: str) -> None:
    """
    Tabela de status por fornecedor com menu de acoes por linha via st.popover.
    """
    st.markdown(
        '<div class="kmt-card" style="padding:14px 20px;margin-bottom:4px;">'
        f'<span class="kmt-card-label">Status por Fornecedor \u2014 {period_lbl}</span>'
        f'<span style="font-size:11px;color:#9CA3AF;margin-left:12px;">{len(rows)} fornecedor(es)</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not rows:
        st.markdown(
            '<div style="padding:30px;text-align:center;color:#9CA3AF;font-size:13px;">'
            'Nenhum fornecedor encontrado para os filtros selecionados.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Cabecalho
    hdr = st.columns(_ADM_COLS)
    labels = ["Fornecedor", "Codigo", "Periodo", "Status", "Ultimo Envio", "Versao", "Acoes"]
    for col, lbl in zip(hdr, labels):
        with col:
            st.markdown(
                f'<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:.06em;color:#9CA3AF;margin:0;">{lbl}</p>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<hr style="margin:6px 0 2px;border:none;border-top:2px solid #E5E7EB;">',
        unsafe_allow_html=True,
    )

    # Linhas
    for r in rows:
        row_cols = st.columns(_ADM_COLS)

        with row_cols[0]:
            st.markdown(
                f'<p style="font-size:13px;font-weight:700;color:#002B5C;margin:6px 0;">'
                f'{r["name"]}</p>',
                unsafe_allow_html=True,
            )
        with row_cols[1]:
            st.markdown(
                f'<p style="font-family:monospace;font-size:12px;color:#6B7280;margin:6px 0;">'
                f'{r["code"]}</p>',
                unsafe_allow_html=True,
            )
        with row_cols[2]:
            period_display = _period_label(r["period"]) if r["period"] != "\u2014" else "\u2014"
            st.markdown(
                f'<p style="font-size:12px;color:#2563EB;margin:6px 0;">{period_display}</p>',
                unsafe_allow_html=True,
            )
        with row_cols[3]:
            st.markdown(
                f'<div style="margin:4px 0;">{status_badge(r["status"])}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[4]:
            st.markdown(
                f'<p style="font-size:11px;color:#6B7280;margin:6px 0;">{r["last"]}</p>',
                unsafe_allow_html=True,
            )
        with row_cols[5]:
            ver_html = (
                version_badge(r["version"])
                if isinstance(r["version"], int)
                else f'<span style="color:#9CA3AF;font-size:12px;">{r["version"]}</span>'
            )
            st.markdown(
                f'<div style="margin:4px 0;">{ver_html}</div>',
                unsafe_allow_html=True,
            )

        # Menu de acoes via popover
        with row_cols[6]:
            upload_id = r.get("upload_id")
            has_actions = upload_id and r["status"] in ("recebido", "cancelled_pending")

            if has_actions:
                with st.popover("\u22ee", use_container_width=True):
                    st.markdown(
                        f'<p style="font-size:11px;font-weight:700;color:#002B5C;'
                        f'margin:0 0 8px;padding-bottom:6px;'
                        f'border-bottom:1px solid #F3F4F6;">'
                        f'{r["name"]}</p>',
                        unsafe_allow_html=True,
                    )

                    if r["status"] == "recebido":
                        st.button(
                            "Ver Detalhes",
                            key=f"adm_pop_det_{upload_id}",
                            use_container_width=True,
                            on_click=_cb_adm_ver_detalhe,
                            args=(upload_id,),
                        )
                    elif r["status"] == "cancelled_pending":
                        st.button(
                            "Ver Cancelamento",
                            key=f"adm_pop_canc_{upload_id}",
                            use_container_width=True,
                            on_click=_cb_adm_ver_detalhe,
                            args=(upload_id,),
                        )
            else:
                st.markdown(
                    '<p style="font-size:11px;color:#D1D5DB;margin:6px 0;">\u2014</p>',
                    unsafe_allow_html=True,
                )

        # Separador
        st.markdown(
            '<div style="border-top:1px solid #F3F4F6;margin:0;"></div>',
            unsafe_allow_html=True,
        )


def _render_quick_nav() -> None:
    """Atalhos rápidos para as principais telas administrativas."""
    st.markdown(
        '<div class="kmt-card" style="padding:14px 20px;margin-bottom:4px;">'
        '<p class="kmt-card-label">Navegação Rápida</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2, _ = st.columns([2, 2, 4])

    with col1:
        if st.button(
            "🏭  Gestão de Fornecedores",
            key="dn_suppliers",
            use_container_width=True,
        ):
            navigate_to("admin_suppliers", origin="admin_dashboard")
            safe_rerun()

    with col2:
        if st.button(
            "✅  Forecasts Recebidos",
            key="dn_validated",
            use_container_width=True,
        ):
            navigate_to("validated_data", origin="admin_dashboard")
            safe_rerun()



# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """
    Renderiza o painel administrativo de coleta.
    Chamado por streamlit_app.py quando page == 'admin_dashboard'.

    Fluxo:
    1. Header estático
    2. Filtros (período, fornecedor, status)
    3. Buscar rows para o período selecionado
    4. Aplicar filtros de fornecedor/status
    5. KPIs + tabela + botões de ação
    """
    try:
        _render_impl()
    except Exception as exc:
        from utils.logger import get_logger
        get_logger(__name__).exception("Erro ao renderizar Painel Admin: %s", exc)
        st.error("Não foi possível carregar estas informações no momento. Tente novamente em alguns instantes.")


def _render_impl() -> None:
    """Implementação interna do painel admin."""
    _render_page_header()

    # Seletor de tipo de relatório
    enabled_types = get_enabled_report_types()
    selected_report_type = st.selectbox(
        "Tipo de Relatório",
        options=enabled_types,
        index=0,
        key="adm_report_type",
    )

    periods = _get_available_periods()
    selected_period, selected_suppliers, selected_statuses = _render_filters(periods)

    period_lbl = _period_label(selected_period) if selected_period else "Período atual"

    rows = get_admin_status_rows(period=selected_period, report_type=selected_report_type)
    rows = _apply_filters(rows, selected_suppliers, selected_statuses)

    # Conta uploads válidos cancelados no período (para o card "Envios Cancelados")
    canceled_count = get_canceled_uploads_count(selected_period) if selected_period else 0

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    _render_kpi_cards(rows, period_lbl, canceled_count)

    _render_quick_nav()

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)
    _render_status_table(rows, period_lbl)
