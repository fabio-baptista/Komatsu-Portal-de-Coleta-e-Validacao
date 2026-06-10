"""
supplier_history.py

Tela de histórico de envios do fornecedor.
Lista todos os arquivos enviados com status, versão, data e ação de cancelamento
dentro da janela de tempo permitida.
"""

import streamlit as st

from components.badges import status_badge, version_badge
from components.cards import metric_card, render_cards_row
from services.upload_service import UploadRecord, can_cancel, get_supplier_uploads, persist_cancel_upload
from utils.session_state import navigate_to, deactivate_validated_forecast
from utils.logger import get_logger
from utils.streamlit_compat import safe_rerun

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Componentes internos da tela
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        '<div class="kmt-section">'
        '<p class="kmt-section-title">Histórico de Envios</p>'
        '<p class="kmt-section-subtitle">'
        'Acompanhe os arquivos enviados, versões e status de processamento.'
        '</p></div>',
        unsafe_allow_html=True,
    )


def _render_summary_cards(records: list[UploadRecord]) -> None:
    """Exibe os 4 cards de resumo operacional."""
    total = len(records)
    valid_count    = sum(1 for r in records if r.status == "valid")
    invalid_count  = sum(1 for r in records if r.status == "invalid")

    # Versão ativa = maior versão dentre os registros com status "valid"
    active_versions = [r.version for r in records if r.status == "valid"]
    active_version  = f"v.{max(active_versions)}" if active_versions else "—"

    render_cards_row([
        metric_card("Total de Envios",  str(total)),
        metric_card("Versão Ativa",     active_version),
        metric_card("Arquivos Válidos", str(valid_count)),
        metric_card("Com Erro",         str(invalid_count)),
    ])


def _render_history_table(records: list[UploadRecord]) -> str:
    """
    Retorna HTML da tabela de histórico.
    Colunas: Upload ID, Arquivo, Período, Versão, Status, Data Envio,
             Linhas Válidas, Linhas c/ Erro.
    A coluna "Ação" foi removida — ações reais ficam nos botões abaixo da tabela.
    """
    rows = ""
    for r in records:
        badge   = status_badge(r.status)
        ver     = version_badge(r.version)
        valid_c = (
            f'<span style="color:#15803D;font-weight:700;">{r.valid_rows}</span>'
            if r.valid_rows > 0 else
            '<span style="color:#9CA3AF;">0</span>'
        )
        invalid_c = (
            f'<span style="color:#B91C1C;font-weight:700;">{r.invalid_rows}</span>'
            if r.invalid_rows > 0 else
            '<span style="color:#9CA3AF;">0</span>'
        )

        rows += (
            f'<tr class="kmt-table-row" id="row-{r.upload_id}">'
            f'<td class="kmt-table-cell kmt-td-id">{r.upload_id}</td>'
            f'<td class="kmt-table-cell" style="max-width:220px;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;" title="{r.file_name}">'
            f'{r.file_name}</td>'
            f'<td class="kmt-table-cell kmt-td-period">{r.period}</td>'
            f'<td class="kmt-table-cell kmt-td-center">{ver}</td>'
            f'<td class="kmt-table-cell">{badge}</td>'
            f'<td class="kmt-table-cell kmt-td-date">{r.sent_at}</td>'
            f'<td class="kmt-table-cell kmt-td-center">{valid_c}</td>'
            f'<td class="kmt-table-cell kmt-td-center">{invalid_c}</td>'
            '</tr>'
        )

    return (
        '<div class="kmt-table-container">'
        '<div class="kmt-table-header">'
        '<span class="kmt-table-title">Rastreabilidade de Arquivos</span>'
        '</div>'
        '<div class="kmt-table-scroll">'
        '<table class="kmt-table">'
        '<thead><tr class="kmt-thead-row">'
        '<th class="kmt-th">Upload ID</th>'
        '<th class="kmt-th">Arquivo</th>'
        '<th class="kmt-th">Período</th>'
        '<th class="kmt-th kmt-th-center">Versão</th>'
        '<th class="kmt-th">Status</th>'
        '<th class="kmt-th">Data Envio</th>'
        '<th class="kmt-th kmt-th-center">Linhas Válidas</th>'
        '<th class="kmt-th kmt-th-center">Linhas c/ Erro</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody>'
        '</table></div></div>'
    )


# ---------------------------------------------------------------------------
# Mapeamento de labels de status
# ---------------------------------------------------------------------------

_STATUS_LABELS = {
    "invalid": "Inválido",
    "valid": "Válido",
    "replaced": "Substituído",
    "canceled": "Cancelado",
}


def _render_actions_with_filters(records: list[UploadRecord]) -> None:
    """
    Seção de ações com filtros interconectados.

    Filtros: Status, Upload ID, Arquivo, Período, Versão.
    Ao filtrar por status, apenas os uploads com aquele status ficam
    disponíveis nos demais filtros. Ações contextuais:
      - "Ver erros" → apenas status inválido
      - "Ver Detalhes" → válido, substituído, cancelado
      - "Cancelar Envio" → válido ativo dentro da janela aberta
    """
    # Banner de sucesso do último cancelamento
    just_cancelled_id = st.session_state.get("just_cancelled_upload_id")
    if just_cancelled_id:
        st.session_state.just_cancelled_upload_id = None
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-bottom:12px;">'
            '<div class="kmt-alert-icon">✅</div>'
            '<div>'
            '<p class="kmt-alert-title">Envio cancelado com sucesso.</p>'
            '<p class="kmt-alert-body">'
            f'O registro <strong>{just_cancelled_id}</strong> foi mantido '
            'no histórico com status <strong>Cancelado</strong> '
            'e deixou de ser a versão ativa.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="kmt-card" style="padding:16px 20px;">'
        '<p class="kmt-card-label" style="margin-bottom:10px;">'
        'Ações</p></div>',
        unsafe_allow_html=True,
    )

    # --- Filtro 1: Status ---
    all_statuses = sorted({r.status for r in records})
    status_options = [_STATUS_LABELS.get(s, s) for s in all_statuses]

    col_st, col_arq, col_per, col_ver, col_id = st.columns(5)

    with col_st:
        selected_status_label = st.selectbox(
            "Status",
            options=["Todos"] + status_options,
            key="hist_filter_status",
        )

    # Resolve label de volta para valor interno
    _label_to_key = {v: k for k, v in _STATUS_LABELS.items()}
    selected_status = _label_to_key.get(selected_status_label)  # None se "Todos"

    # Filtra records pelo status selecionado
    if selected_status:
        filtered = [r for r in records if r.status == selected_status]
    else:
        filtered = list(records)

    # --- Filtro 2: Arquivo ---
    file_options = sorted({r.file_name for r in filtered})
    with col_arq:
        selected_file = st.selectbox(
            "Arquivo",
            options=["Todos"] + file_options,
            key="hist_filter_file",
        )
    if selected_file != "Todos":
        filtered = [r for r in filtered if r.file_name == selected_file]

    # --- Filtro 3: Período ---
    period_options = sorted({r.period for r in filtered})
    with col_per:
        selected_period = st.selectbox(
            "Período",
            options=["Todos"] + period_options,
            key="hist_filter_period",
        )
    if selected_period != "Todos":
        filtered = [r for r in filtered if r.period == selected_period]

    # --- Filtro 4: Versão ---
    version_options = sorted({str(r.version) for r in filtered})
    with col_ver:
        selected_version = st.selectbox(
            "Versão",
            options=["Todos"] + version_options,
            key="hist_filter_version",
        )
    if selected_version != "Todos":
        filtered = [r for r in filtered if str(r.version) == selected_version]

    # --- Filtro 5: Upload ID ---
    id_options = [r.upload_id for r in filtered]
    with col_id:
        selected_id = st.selectbox(
            "Upload ID",
            options=["Todos"] + id_options,
            key="hist_filter_id",
        )
    if selected_id != "Todos":
        filtered = [r for r in filtered if r.upload_id == selected_id]

    # --- Resultado do filtro ---
    if not filtered:
        st.markdown(
            '<div style="padding:12px 0;font-size:13px;color:#6B7280;">'
            'Nenhum envio encontrado com os filtros selecionados.</div>',
            unsafe_allow_html=True,
        )
        return

    # Se mais de 1 resultado, solicita refinamento
    if len(filtered) > 1:
        st.markdown(
            '<div style="padding:12px 0;font-size:13px;color:#6B7280;">'
            f'{len(filtered)} envio(s) encontrados. '
            'Refine os filtros para selecionar um envio específico e ver as ações disponíveis.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Exatamente 1 registro selecionado → mostrar ações
    record = filtered[0]

    st.markdown(
        '<div style="padding:10px 0 6px 0;font-size:13px;color:#374151;">'
        f'<strong style="color:#002B5C;">{record.upload_id}</strong>'
        f'&nbsp;·&nbsp;{record.file_name}'
        f'&nbsp;·&nbsp;{status_badge(record.status)}'
        f'&nbsp;·&nbsp;<span style="font-size:11px;color:#6B7280;">'
        f'v{record.version} · {record.period} · {record.sent_at}</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Ações contextuais
    action_cols = st.columns(3)

    # Ver erros — apenas para inválidos
    if record.status == "invalid":
        with action_cols[0]:
            if st.button(
                "Ver erros",
                key=f"btn_errors_{record.upload_id}",
                use_container_width=True,
            ):
                navigate_to("errors", upload_id=record.upload_id, origin="history")
                safe_rerun()

    # Ver Detalhes — para válido, substituído, cancelado
    if record.status in ("valid", "replaced", "canceled"):
        with action_cols[1]:
            if st.button(
                "Ver Detalhes",
                key=f"btn_detail_{record.upload_id}",
                use_container_width=True,
            ):
                navigate_to(
                    "admin_upload_detail",
                    upload_id=record.upload_id,
                    origin="history",
                )
                safe_rerun()

    # Cancelar Envio — apenas para válido ativo dentro da janela
    if can_cancel(record):
        with action_cols[2]:
            if st.button(
                "Cancelar Envio",
                key=f"btn_cancel_{record.upload_id}",
                use_container_width=True,
            ):
                supplier_id = st.session_state.get("supplier_id") or ""
                user_email = st.session_state.get("user_email", "—")
                success = persist_cancel_upload(
                    upload_id=record.upload_id,
                    supplier_id=supplier_id,
                    cancelled_by=user_email,
                )
                if success:
                    _logger.info(
                        "Upload cancelado com sucesso: upload_id=%s, by=%s",
                        record.upload_id, user_email,
                    )
                    deactivate_validated_forecast(record.upload_id)
                    st.session_state.just_cancelled_upload_id = record.upload_id
                else:
                    _logger.error(
                        "Falha ao cancelar upload: upload_id=%s", record.upload_id,
                    )
                    st.error(
                        "Falha ao cancelar o envio no Snowflake. "
                        "Verifique se o envio ainda está ativo e tente novamente."
                    )
                safe_rerun()


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """
    Renderiza a tela de histórico de envios do fornecedor.
    Chamado por streamlit_app.py quando page == 'history'.
    O supplier_id vem do session_state (não da planilha).
    Exibe apenas uploads registrados na sessão atual (include_mock=False).
    """
    try:
        _render_impl()
    except Exception as exc:
        _logger.exception("Erro ao renderizar Meus Envios: %s", exc)
        st.error("Não foi possível carregar estas informações no momento. Tente novamente em alguns instantes.")


def _render_impl() -> None:
    """Implementação interna da tela de histórico."""
    supplier_id = st.session_state.get("supplier_id") or ""

    records = get_supplier_uploads(supplier_id, include_mock=False)

    _render_page_header()
    _render_summary_cards(records)

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)

    if not records:
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-top:8px;">'
            '<div class="kmt-alert-icon">📭</div>'
            '<div>'
            '<p class="kmt-alert-title">Nenhum envio encontrado para este fornecedor.</p>'
            '<p class="kmt-alert-body">'
            'Use <strong>Enviar Arquivo</strong> para registrar seu primeiro forecast.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
        return

    # Tabela principal
    st.markdown(_render_history_table(records), unsafe_allow_html=True)

    # Filtros interconectados + ações contextuais
    _render_actions_with_filters(records)
