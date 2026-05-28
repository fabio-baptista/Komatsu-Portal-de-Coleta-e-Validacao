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
from utils.session_state import navigate_to
from utils.streamlit_compat import safe_rerun


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_STATUS_PT: dict[str, str] = {
    "valid":    "Válido",
    "invalid":  "Inválido",
    "pending":  "Pendente",
    "canceled": "Cancelado",
    "replaced": "Substituído",
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
        """
        <div class="kmt-section">
            <p class="kmt-section-title">Painel de Coleta de Forecast</p>
            <p class="kmt-section-subtitle">
                Acompanhamento do ciclo de envio de forecast por fornecedor.
                Utilize os filtros abaixo para selecionar período e fornecedores.
            </p>
        </div>
        """,
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
    4 cards KPI orientados à coleta de forecast.

    Regra de negócio:
      Participantes   = fornecedores ativos na coleta do período (CONTROL.SUPPLIERS)
      Válidos         = com upload VALID e IS_ACTIVE=TRUE no período (CONTROL.UPLOAD_BATCHES)
      Pendentes       = sem forecast válido ativo (inclui sem envio, com inválido e cancelados
                        que não reenviaram)
      Cancelados      = uploads STATUS=CANCELLED no período (CONTROL.UPLOAD_BATCHES)
    """
    participantes = len(rows)
    validos       = sum(1 for r in rows if r["status"] == "valid")
    pendentes     = participantes - validos
    sem_valido    = pendentes

    render_cards_row([
        kpi_card("Participantes",            str(participantes)),
        kpi_card("Enviaram Forecast Válido", str(validos)),
        kpi_card("Pendentes",                str(pendentes)),
        kpi_card("Envios Cancelados",        str(canceled_count)),
    ])

    # Nota de rastreabilidade
    if sem_valido > 0:
        st.markdown(
            f'<p style="font-size:12px;color:#B45309;font-weight:600;margin:6px 0 0 2px;">'
            f'⚠&nbsp;&nbsp;{sem_valido} fornecedor(es) sem forecast válido no período.</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<p style="font-size:12px;color:#15803D;font-weight:600;margin:6px 0 0 2px;">'
            f'✓&nbsp;&nbsp;Todos os {participantes} fornecedores '
            f'entregaram forecast válido no período.</p>',
            unsafe_allow_html=True,
        )

    if canceled_count > 0:
        st.markdown(
            f'<p style="font-size:11px;color:#6B7280;margin:3px 0 0 2px;">'
            f'ℹ&nbsp;&nbsp;{canceled_count} envio(s) válido(s) cancelado(s) no período — '
            f'consulte o histórico individual para detalhes.</p>',
            unsafe_allow_html=True,
        )

    # Nota explicativa sobre as definições
    st.markdown(
        f'<p style="font-size:11px;color:#9CA3AF;margin:4px 0 12px 2px;">'
        f'Período de referência: <strong style="color:#6B7280;">{period_lbl}</strong>'
        f'&nbsp;·&nbsp;'
        f'<strong>Participantes</strong> = fornecedores ativos com coleta habilitada'
        f'&nbsp;·&nbsp;'
        f'<strong>Pendentes</strong> = sem forecast válido ativo (inclui inválidos e cancelados sem reenvio)'
        f'&nbsp;·&nbsp;'
        f'<strong>Cancelados</strong> = eventos de cancelamento de envio válido no período.</p>',
        unsafe_allow_html=True,
    )


def _render_status_table(rows: list[dict], period_lbl: str) -> str:
    """
    HTML da tabela de status por fornecedor.
    Colunas: Fornecedor, Código, Período, Status da Coleta,
             Último Envio, Versão Ativa, Erros.
    Ações clicáveis ficam em _render_action_buttons(), abaixo da tabela.
    """
    if not rows:
        return f"""
        <div class="kmt-table-container">
            <div class="kmt-table-header">
                <span class="kmt-table-title">
                    Status por Fornecedor — {period_lbl}
                </span>
            </div>
            <div style="padding:40px;text-align:center;color:#9CA3AF;font-size:13px;">
                Nenhum fornecedor encontrado para os filtros selecionados.
            </div>
        </div>"""

    table_rows = ""
    for r in rows:
        badge = status_badge(r["status"])

        ver_html = (
            version_badge(r["version"])
            if isinstance(r["version"], int)
            else f'<span style="color:#9CA3AF;font-size:12px;">{r["version"]}</span>'
        )

        errors_html = (
            f'<span style="color:#B91C1C;font-weight:700;">{r["errors"]}</span>'
            if isinstance(r["errors"], int) and r["errors"] > 0
            else f'<span style="color:#9CA3AF;">—</span>'
        )

        period_display = _period_label(r["period"]) if r["period"] != "—" else "—"

        table_rows += f"""
        <tr class="kmt-table-row">
            <td class="kmt-table-cell"
                style="font-weight:700;color:#002B5C;">{r['name']}</td>
            <td class="kmt-table-cell"
                style="font-family:monospace;font-size:12px;
                       color:#6B7280;">{r['code']}</td>
            <td class="kmt-table-cell"
                style="color:#2563EB;font-size:12px;">{period_display}</td>
            <td class="kmt-table-cell">{badge}</td>
            <td class="kmt-table-cell kmt-td-date">{r['last']}</td>
            <td class="kmt-table-cell kmt-td-center">{ver_html}</td>
            <td class="kmt-table-cell kmt-td-center">{errors_html}</td>
        </tr>"""

    return f"""
    <div class="kmt-table-container">
        <div class="kmt-table-header">
            <span class="kmt-table-title">
                Status por Fornecedor — {period_lbl}
            </span>
            <span style="font-size:11px;color:#9CA3AF;">{len(rows)} fornecedor(es)</span>
        </div>
        <div class="kmt-table-scroll">
            <table class="kmt-table">
                <thead>
                    <tr class="kmt-thead-row">
                        <th class="kmt-th">Fornecedor</th>
                        <th class="kmt-th">Código</th>
                        <th class="kmt-th">Período</th>
                        <th class="kmt-th">Status da Coleta</th>
                        <th class="kmt-th">Último Envio</th>
                        <th class="kmt-th kmt-th-center">Versão Ativa</th>
                        <th class="kmt-th kmt-th-center">Erros</th>
                    </tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
    </div>"""


def _render_quick_nav() -> None:
    """Atalhos rápidos para as principais telas administrativas."""
    st.markdown(
        """
        <div class="kmt-card" style="padding:14px 20px;margin-bottom:4px;">
            <p class="kmt-card-label">Navegação Rápida</p>
        </div>
        """,
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


def _render_action_buttons(rows: list[dict]) -> None:
    """
    Botões de ação inline por fornecedor: Ver detalhe (válidos) / Ver erros (inválidos).
    Usa upload_ids dinâmicos do get_admin_status_rows().
    """
    actionable = [
        r for r in rows
        if r.get("upload_id") and r["status"] in ("valid", "invalid", "replaced")
    ]
    if not actionable:
        return

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="kmt-card" style="padding:14px 20px;margin-bottom:4px;">
            <p class="kmt-card-label">Ações por Fornecedor</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for row in actionable:
        col_info, col_btn, _ = st.columns([4, 2, 2])

        with col_info:
            err_html = (
                f' &nbsp;·&nbsp; <span style="color:#B91C1C;font-weight:600;">'
                f'{row["errors"]} erro(s)</span>'
            ) if isinstance(row.get("errors"), int) and row["errors"] > 0 else ""

            st.markdown(
                f"""
                <div style="padding:8px 0;font-size:13px;color:#374151;">
                    <strong style="color:#002B5C;">{row['name']}</strong>
                    &nbsp;·&nbsp;
                    <span style="font-family:monospace;font-size:12px;color:#6B7280;">
                        {row['upload_id']}
                    </span>
                    {err_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_btn:
            if row["status"] == "invalid":
                if st.button(
                    "Ver erros",
                    key=f"adm_err_{row['upload_id']}",
                    use_container_width=True,
                ):
                    navigate_to(
                        "errors",
                        upload_id=row["upload_id"],
                        origin="admin_dashboard",
                    )
                    safe_rerun()
            else:
                if st.button(
                    "Ver detalhe",
                    key=f"adm_det_{row['upload_id']}",
                    use_container_width=True,
                ):
                    navigate_to(
                        "admin_upload_detail",
                        upload_id=row["upload_id"],
                        origin="admin_dashboard",
                    )
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
    _render_page_header()

    periods = _get_available_periods()
    selected_period, selected_suppliers, selected_statuses = _render_filters(periods)

    period_lbl = _period_label(selected_period) if selected_period else "Período atual"

    rows = get_admin_status_rows(period=selected_period)
    rows = _apply_filters(rows, selected_suppliers, selected_statuses)

    # Conta uploads válidos cancelados no período (para o card "Envios Cancelados")
    canceled_count = get_canceled_uploads_count(selected_period) if selected_period else 0

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    _render_kpi_cards(rows, period_lbl, canceled_count)

    _render_quick_nav()

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)
    st.markdown(_render_status_table(rows, period_lbl), unsafe_allow_html=True)

    _render_action_buttons(rows)
