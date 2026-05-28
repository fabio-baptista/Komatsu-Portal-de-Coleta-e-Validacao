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
from services.mock_data_service import get_current_open_window
from utils.session_state import navigate_to, deactivate_validated_forecast
from utils.logger import get_logger
from utils.streamlit_compat import safe_rerun

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_window_label(window: dict | None) -> str:
    """Formata label da janela de forma defensiva, sem KeyError."""
    if not window:
        return "—"
    label = window.get("label", "Janela atual")
    closes = window.get("closes_at") or window.get("end_date")
    if closes and closes != "—":
        return f"{label} · encerra em {closes}"
    return label


# ---------------------------------------------------------------------------
# Componentes internos da tela
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        """
        <div class="kmt-section">
            <p class="kmt-section-title">Histórico de Envios</p>
            <p class="kmt-section-subtitle">
                Acompanhe os arquivos enviados, versões e status de processamento.
            </p>
        </div>
        """,
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


def _action_label(record: UploadRecord) -> str:
    """Retorna o label da ação disponível para cada linha."""
    if record.status == "invalid":
        return "Ver erros"
    return "Ver detalhe"


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

        rows += f"""
        <tr class="kmt-table-row" id="row-{r.upload_id}">
            <td class="kmt-table-cell kmt-td-id">{r.upload_id}</td>
            <td class="kmt-table-cell" style="max-width:220px;overflow:hidden;
                text-overflow:ellipsis;white-space:nowrap;" title="{r.file_name}">
                {r.file_name}
            </td>
            <td class="kmt-table-cell kmt-td-period">{r.period}</td>
            <td class="kmt-table-cell kmt-td-center">{ver}</td>
            <td class="kmt-table-cell">{badge}</td>
            <td class="kmt-table-cell kmt-td-date">{r.sent_at}</td>
            <td class="kmt-table-cell kmt-td-center">{valid_c}</td>
            <td class="kmt-table-cell kmt-td-center">{invalid_c}</td>
        </tr>"""

    return f"""
    <div class="kmt-table-container">
        <div class="kmt-table-header">
            <span class="kmt-table-title">Rastreabilidade de Arquivos</span>
        </div>
        <div class="kmt-table-scroll">
            <table class="kmt-table">
                <thead>
                    <tr class="kmt-thead-row">
                        <th class="kmt-th">Upload ID</th>
                        <th class="kmt-th">Arquivo</th>
                        <th class="kmt-th">Período</th>
                        <th class="kmt-th kmt-th-center">Versão</th>
                        <th class="kmt-th">Status</th>
                        <th class="kmt-th">Data Envio</th>
                        <th class="kmt-th kmt-th-center">Linhas Válidas</th>
                        <th class="kmt-th kmt-th-center">Linhas c/ Erro</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>"""


def _render_cancel_section(records: list[UploadRecord]) -> None:
    """
    Exibe cancelamento direto para uploads elegíveis.

    Elegibilidade (avaliada por can_cancel):
    - is_active = True
    - status == "valid"
    - period dentro da janela de envio aberta

    Ao clicar "Cancelar envio": executa cancelamento imediato (sem confirmação),
    armazena ID cancelado no session_state e recarrega a página.
    """
    # Banner de sucesso do último cancelamento (exibido apenas uma vez)
    just_cancelled_id = st.session_state.get("just_cancelled_upload_id")
    if just_cancelled_id:
        st.session_state.just_cancelled_upload_id = None
        st.markdown(
            f"""
            <div class="kmt-alert kmt-alert--info" style="margin-bottom:12px;">
                <div class="kmt-alert-icon">✅</div>
                <div>
                    <p class="kmt-alert-title">Envio cancelado com sucesso.</p>
                    <p class="kmt-alert-body">
                        O registro <strong>{just_cancelled_id}</strong> foi mantido
                        no histórico com status <strong>Cancelado</strong>
                        e deixou de ser a versão ativa.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    cancelable = [r for r in records if can_cancel(r)]
    if not cancelable:
        return

    window = get_current_open_window()
    window_label = _format_window_label(window)

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="kmt-card" style="padding:16px 20px;">
            <p class="kmt-card-label" style="margin-bottom:6px;">
                Cancelamento disponível — Janela aberta
            </p>
            <p style="font-size:11px;color:#6B7280;margin:0;">
                {window_label}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_email = st.session_state.get("user_email", "—")

    for record in cancelable:
        col_info, col_btn, _ = st.columns([4, 2, 2])
        with col_info:
            st.markdown(
                f"""
                <div style="padding:8px 0;font-size:13px;color:#374151;">
                    <strong style="color:#002B5C;">{record.upload_id}</strong>
                    &nbsp;·&nbsp;{record.file_name}
                    &nbsp;·&nbsp;{status_badge(record.status)}
                    &nbsp;·&nbsp;
                    <span style="font-size:11px;color:#6B7280;">
                        v{record.version} · {record.period}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button(
                "Cancelar envio",
                key=f"btn_cancel_{record.upload_id}",
                use_container_width=True,
            ):
                supplier_id = st.session_state.get("supplier_id") or ""
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
                    # Desativar forecasts validados na sessão (temporário)
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

    st.markdown(
        """
        <div style="margin-top:12px;padding:10px 16px;background:#F9FAFB;
                    border-left:3px solid #E5E7EB;border-radius:4px;">
            <p style="font-size:11px;color:#9CA3AF;margin:0;">
                ⚠&nbsp; O cancelamento é lógico — o registro permanece no histórico
                com status <strong>Cancelado</strong> e deixa de ser a versão ativa.
                Só é permitido para o upload ativo dentro da janela aberta.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_action_buttons(records: list[UploadRecord]) -> None:
    """
    Renderiza botões de ação para registros com status inválido.
    O botão "Ver erros" navega para a tela supplier_errors.
    """
    invalid_records = [r for r in records if r.status == "invalid"]
    if not invalid_records:
        return

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="kmt-card" style="padding:16px 20px;">
            <p class="kmt-card-label" style="margin-bottom:10px;">
                Ações — Arquivos com Erros
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for record in invalid_records:
        col_info, col_btn, _ = st.columns([4, 2, 2])
        with col_info:
            st.markdown(
                f"""
                <div style="padding:8px 0;font-size:13px;color:#374151;">
                    <strong style="color:#002B5C;">{record.upload_id}</strong>
                    &nbsp;·&nbsp;{record.file_name}
                    &nbsp;·&nbsp;{status_badge(record.status)}
                    &nbsp;·&nbsp;<span style="color:#B91C1C;font-weight:600;">
                        {record.invalid_rows} erro(s)
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button(
                "Ver erros",
                key=f"btn_errors_{record.upload_id}",
                use_container_width=True,
            ):
                navigate_to("errors", upload_id=record.upload_id, origin="history")
                safe_rerun()


def _render_detail_buttons(records: list[UploadRecord]) -> None:
    """
    Renderiza botões "Ver detalhe" para registros válidos ou substituídos.
    Navega para a tela de Detalhe do Envio com o upload selecionado.
    """
    detail_records = [r for r in records if r.status in ("valid", "replaced", "canceled")]
    if not detail_records:
        return

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    for record in detail_records:
        col_info, col_btn, _ = st.columns([4, 2, 2])
        with col_info:
            st.markdown(
                f"""
                <div style="padding:8px 0;font-size:13px;color:#374151;">
                    <strong style="color:#002B5C;">{record.upload_id}</strong>
                    &nbsp;·&nbsp;{record.file_name}
                    &nbsp;·&nbsp;{status_badge(record.status)}
                    &nbsp;·&nbsp;<span style="color:#6B7280;font-size:12px;">
                        {record.period} · v{record.version}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button(
                "Ver detalhe",
                key=f"btn_detail_{record.upload_id}",
                use_container_width=True,
            ):
                navigate_to(
                    "admin_upload_detail",
                    upload_id=record.upload_id,
                    origin="history",
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
    supplier_id = st.session_state.get("supplier_id") or ""

    records = get_supplier_uploads(supplier_id, include_mock=False)

    _render_page_header()
    _render_summary_cards(records)

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)

    if not records:
        st.markdown(
            """
            <div class="kmt-alert kmt-alert--info" style="margin-top:8px;">
                <div class="kmt-alert-icon">📭</div>
                <div>
                    <p class="kmt-alert-title">Nenhum envio encontrado para este fornecedor.</p>
                    <p class="kmt-alert-body">
                        Use <strong>Enviar Arquivo</strong> para registrar seu primeiro forecast.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Tabela principal
    st.markdown(_render_history_table(records), unsafe_allow_html=True)

    # Botões de ação para inválidos (navega para tela de erros)
    _render_action_buttons(records)

    # Botões de detalhe para válidos/substituídos/cancelados
    _render_detail_buttons(records)

    # Ações de cancelamento (inclui aviso de janela)
    _render_cancel_section(records)
