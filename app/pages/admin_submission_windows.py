"""
admin_submission_windows.py

Tela administrativa para gerenciamento de Janelas de Envio.
Permite visualizar janela aberta, criar novas janelas e fechar/abrir janelas existentes.
"""

from datetime import date, datetime

import streamlit as st

from services.submission_window_service import (
    get_current_open_window,
    list_submission_windows,
    create_submission_window,
    close_submission_window,
    open_submission_window,
)
from utils.constants import DEFAULT_REPORT_TYPE
from utils.logger import get_logger
from utils.streamlit_compat import safe_rerun

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date_br(date_str: str) -> date | None:
    """Parse DD/MM/YYYY to date object."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def _window_status_badge(w: dict, today: date) -> str:
    """
    Retorna badge HTML contextual:
    - VIGENTE: IS_OPEN=True e hoje entre inicio/fim
    - EXPIRADA: IS_OPEN=True mas data final < hoje
    - FUTURA: IS_OPEN=True mas data inicial > hoje
    - FECHADA: IS_OPEN=False
    """
    is_open = w.get("is_open", False)

    if not is_open:
        return (
            '<span style="background:#F3F4F6;color:#6B7280;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">FECHADA</span>'
        )

    start_d = _parse_date_br(w.get("start_date", ""))
    end_d = _parse_date_br(w.get("end_date", ""))

    if end_d and end_d < today:
        return (
            '<span style="background:#FEF2F2;color:#B91C1C;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">EXPIRADA</span>'
        )

    if start_d and start_d > today:
        return (
            '<span style="background:#EFF6FF;color:#2563EB;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">FUTURA</span>'
        )

    return (
        '<span style="background:#DCFCE7;color:#15803D;padding:2px 8px;'
        'border-radius:4px;font-size:11px;font-weight:600;">VIGENTE</span>'
    )


# ---------------------------------------------------------------------------
# Componentes internos
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        '<div class="kmt-section">'
        '<p class="kmt-section-title">Janelas de Envio</p>'
        '<p class="kmt-section-subtitle">'
        'Gerencie os ciclos de coleta de forecast. '
        'Crie, abra ou feche janelas de envio para controlar o periodo ativo.'
        '</p></div>',
        unsafe_allow_html=True,
    )


def _render_current_window() -> None:
    """Mostra a janela aberta atual ou aviso se nenhuma."""
    window = get_current_open_window()

    if window and window.get("window_id") == "__MOCK__":
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-bottom:12px;">'
            '<div class="kmt-alert-icon">&#9888;</div>'
            '<div>'
            '<p class="kmt-alert-title">Modo demonstracao</p>'
            '<p class="kmt-alert-body">'
            'Nenhuma janela cadastrada no Snowflake. '
            'O sistema esta usando uma janela de demonstracao. '
            'Crie uma janela real abaixo para operar em modo funcional.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
        return

    if window:
        st.markdown(
            '<div class="kmt-alert kmt-alert--success" style="margin-bottom:12px;">'
            '<div class="kmt-alert-icon">&#9989;</div>'
            '<div>'
            '<p class="kmt-alert-title">Janela aberta</p>'
            '<p class="kmt-alert-body">'
            f'<strong>{window.get("report_type", DEFAULT_REPORT_TYPE)}</strong>'
            f' &mdash; Periodo: <strong>{window.get("reference_period", "")}</strong>'
            f' &mdash; {window.get("start_date", "")} a {window.get("end_date", "")}'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="kmt-alert kmt-alert--error" style="margin-bottom:12px;">'
            '<div class="kmt-alert-icon">&#10060;</div>'
            '<div>'
            '<p class="kmt-alert-title">Nenhuma janela de envio aberta</p>'
            '<p class="kmt-alert-body">'
            'Crie ou abra uma janela para iniciar o ciclo de coleta. '
            'Fornecedores nao poderao enviar arquivos enquanto nao houver janela aberta.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )


def _render_create_form() -> None:
    """Formulario para criar nova janela de envio."""
    st.markdown(
        '<div class="kmt-card" style="padding:16px 20px;margin-bottom:16px;">'
        '<p class="kmt-card-label" style="margin-bottom:10px;">'
        'Criar Nova Janela</p></div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        report_type = st.selectbox(
            "Tipo de Relatorio",
            options=[DEFAULT_REPORT_TYPE],
            index=0,
            key="win_form_report_type",
        )

    with col2:
        # Sugerir proximo mes
        today = date.today()
        suggested_period = f"{today.year}-{today.month:02d}"
        reference_period = st.text_input(
            "Periodo de Referencia (YYYY-MM)",
            value=suggested_period,
            key="win_form_period",
            max_chars=7,
        )

    with col3:
        start_date = st.date_input(
            "Data Inicial",
            value=today.replace(day=1),
            key="win_form_start",
        )

    with col4:
        # Sugerir ultimo dia do mes
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = st.date_input(
            "Data Final",
            value=today.replace(day=last_day),
            key="win_form_end",
        )

    col_btn, col_msg, _ = st.columns([2, 4, 2])
    with col_btn:
        if st.button("Criar Janela", key="btn_create_window", use_container_width=True):
            # Validacoes
            import re
            if not re.match(r"^\d{4}-\d{2}$", reference_period):
                st.error("Periodo deve estar no formato YYYY-MM (ex: 2026-06).")
                return

            if start_date > end_date:
                st.error("Data inicial deve ser anterior ou igual a data final.")
                return

            if end_date < today:
                st.error("A data final da janela nao pode ser anterior a data atual.")
                return

            created_by = st.session_state.get("user_email", "admin")
            result = create_submission_window(
                report_type=report_type,
                reference_period=reference_period,
                start_date=start_date,
                end_date=end_date,
                created_by=created_by,
            )

            if result:
                st.session_state["_win_success"] = "Janela de envio criada com sucesso."
                safe_rerun()
            else:
                st.error(
                    "Nao foi possivel criar a janela. "
                    "Verifique se ja existe uma janela aberta sobreposta para este periodo."
                )


def _render_windows_list() -> None:
    """Lista todas as janelas cadastradas com acoes de fechar/abrir."""
    windows = list_submission_windows()

    if not windows:
        st.markdown(
            '<div style="padding:12px 0;font-size:13px;color:#6B7280;">'
            'Nenhuma janela cadastrada.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div class="kmt-card" style="padding:16px 20px;margin-bottom:12px;">'
        '<p class="kmt-card-label" style="margin-bottom:10px;">'
        'Janelas Cadastradas</p></div>',
        unsafe_allow_html=True,
    )

    # Tabela HTML
    today = date.today()
    rows_html = ""
    for w in windows:
        status_html = _window_status_badge(w, today)
        rows_html += (
            '<tr class="kmt-table-row">'
            f'<td class="kmt-table-cell" style="font-family:monospace;font-size:11px;">'
            f'{w.get("window_id", "")[:8]}...</td>'
            f'<td class="kmt-table-cell">{w.get("report_type", "")}</td>'
            f'<td class="kmt-table-cell">{w.get("reference_period", "")}</td>'
            f'<td class="kmt-table-cell">{w.get("start_date", "")}</td>'
            f'<td class="kmt-table-cell">{w.get("end_date", "")}</td>'
            f'<td class="kmt-table-cell">{status_html}</td>'
            f'<td class="kmt-table-cell" style="font-size:11px;color:#6B7280;">'
            f'{w.get("created_by", "")}</td>'
            '</tr>'
        )

    st.markdown(
        '<div class="kmt-table-container">'
        '<div class="kmt-table-scroll">'
        '<table class="kmt-table">'
        '<thead><tr class="kmt-thead-row">'
        '<th class="kmt-th">ID</th>'
        '<th class="kmt-th">Tipo</th>'
        '<th class="kmt-th">Periodo</th>'
        '<th class="kmt-th">Inicio</th>'
        '<th class="kmt-th">Fim</th>'
        '<th class="kmt-th">Status</th>'
        '<th class="kmt-th">Criado por</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div></div>',
        unsafe_allow_html=True,
    )

    # Botoes de acao por janela
    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    user_email = st.session_state.get("user_email", "admin")

    today = date.today()
    for w in windows:
        wid = w.get("window_id", "")
        is_open = w.get("is_open", False)

        # Determinar label textual
        end_d = _parse_date_br(w.get("end_date", ""))
        start_d = _parse_date_br(w.get("start_date", ""))
        if not is_open:
            status_txt = "FECHADA"
        elif end_d and end_d < today:
            status_txt = "EXPIRADA"
        elif start_d and start_d > today:
            status_txt = "FUTURA"
        else:
            status_txt = "VIGENTE"

        col_info, col_btn, _ = st.columns([5, 2, 1])
        with col_info:
            st.markdown(
                f'<div style="padding:6px 0;font-size:12px;color:#374151;">'
                f'<strong>{w.get("reference_period", "")}</strong>'
                f' &mdash; {w.get("start_date", "")} a {w.get("end_date", "")}'
                f' &mdash; {status_txt}'
                '</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if is_open:
                if st.button(
                    "Fechar",
                    key=f"btn_close_{wid}",
                    use_container_width=True,
                ):
                    success = close_submission_window(wid, user_email)
                    if success:
                        st.session_state["_win_success"] = "Janela de envio fechada com sucesso."
                        safe_rerun()
                    else:
                        st.error("Falha ao fechar a janela.")
            else:
                if st.button(
                    "Abrir",
                    key=f"btn_open_{wid}",
                    use_container_width=True,
                ):
                    success = open_submission_window(wid, user_email)
                    if success:
                        st.session_state["_win_success"] = "Janela de envio aberta com sucesso."
                        safe_rerun()
                    else:
                        st.error(
                            "Nao foi possivel abrir a janela. "
                            "Verifique se ha outra janela aberta sobreposta."
                        )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """Renderiza a tela de Janelas de Envio."""
    try:
        _render_impl()
    except Exception as exc:
        _logger.exception("Erro ao renderizar Janelas de Envio: %s", exc)
        st.error(
            "Nao foi possivel carregar estas informacoes no momento. "
            "Tente novamente em alguns instantes."
        )


def _render_impl() -> None:
    """Implementacao interna."""
    _render_page_header()

    # Mensagem de sucesso (flash)
    success_msg = st.session_state.pop("_win_success", None)
    if success_msg:
        st.success(success_msg)

    _render_current_window()

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    _render_create_form()

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)
    _render_windows_list()
