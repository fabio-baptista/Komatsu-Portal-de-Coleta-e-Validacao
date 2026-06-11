"""
supplier_history.py

Tela de historico de envios do fornecedor.
Orientada por Tipo de Relatorio com menu de acoes por linha (padrao popover).
"""

import streamlit as st

from components.badges import status_badge, version_badge
from components.cards import metric_card, render_cards_row
from services.upload_service import UploadRecord, can_cancel, get_supplier_uploads, persist_cancel_upload
from utils.constants import get_enabled_report_types
from utils.session_state import navigate_to, deactivate_validated_forecast
from utils.logger import get_logger
from utils.streamlit_compat import safe_rerun

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Status labels
# ---------------------------------------------------------------------------

_STATUS_LABELS = {
    "invalid": "Inválido",
    "valid": "Válido/Ativo",
    "replaced": "Substituído",
    "canceled": "Cancelado",
}
_LABEL_TO_STATUS = {v: k for k, v in _STATUS_LABELS.items()}

# Proporcoes das colunas da tabela (7 colunas + acoes)
_COLS = [3, 1.2, 0.8, 1.2, 1.5, 0.8, 0.8, 0.7]


# ---------------------------------------------------------------------------
# Callbacks de acao (usados por on_click nos popovers)
# ---------------------------------------------------------------------------

def _cb_ver_erros(upload_id: str) -> None:
    navigate_to("errors", upload_id=upload_id, origin="history")


def _cb_ver_detalhes(upload_id: str) -> None:
    navigate_to("admin_upload_detail", upload_id=upload_id, origin="history")


def _cb_cancelar(upload_id: str, supplier_id: str, user_email: str) -> None:
    success = persist_cancel_upload(
        upload_id=upload_id,
        supplier_id=supplier_id,
        cancelled_by=user_email,
    )
    if success:
        _logger.info("Upload cancelado: upload_id=%s, by=%s", upload_id, user_email)
        deactivate_validated_forecast(upload_id)
        st.session_state.just_cancelled_upload_id = upload_id
    else:
        _logger.error("Falha ao cancelar upload: upload_id=%s", upload_id)
        st.session_state["_hist_cancel_error"] = True


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        '<div class="kmt-section">'
        '<p class="kmt-section-title">Histórico de Envios</p>'
        '<p class="kmt-section-subtitle">'
        'Selecione o tipo de relatório para consultar seus envios.'
        '</p></div>',
        unsafe_allow_html=True,
    )


def _render_summary_cards(records: list[UploadRecord]) -> None:
    total = len(records)
    valid_count = sum(1 for r in records if r.status == "valid")
    invalid_count = sum(1 for r in records if r.status == "invalid")
    active_versions = [r.version for r in records if r.status == "valid"]
    active_version = f"v.{max(active_versions)}" if active_versions else "\u2014"

    render_cards_row([
        metric_card("Total de Envios", str(total)),
        metric_card("Versão Ativa", active_version),
        metric_card("Válidos", str(valid_count)),
        metric_card("Com Erro", str(invalid_count)),
    ])


def _render_table_with_actions(records: list[UploadRecord]) -> None:
    """Tabela com st.columns por linha e popover de acoes na ultima coluna."""
    if not records:
        st.markdown(
            '<div style="padding:24px 0;text-align:center;color:#9CA3AF;font-size:13px;">'
            'Nenhum envio encontrado para o tipo e status selecionados.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Cabecalho
    hdr = st.columns(_COLS)
    labels = ["Arquivo", "Período", "Versão", "Status", "Data Envio", "Válidas", "Erros", "Ações"]
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
    supplier_id = st.session_state.get("supplier_id") or ""
    user_email = st.session_state.get("user_email", "")

    for r in records:
        row = st.columns(_COLS)

        with row[0]:
            st.markdown(
                f'<p style="font-size:12px;color:#374151;margin:6px 0;'
                f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"'
                f' title="{r.file_name}">{r.file_name}</p>',
                unsafe_allow_html=True,
            )
        with row[1]:
            st.markdown(
                f'<p style="font-size:12px;color:#374151;margin:6px 0;">{r.period}</p>',
                unsafe_allow_html=True,
            )
        with row[2]:
            st.markdown(
                f'<div style="margin:4px 0;">{version_badge(r.version)}</div>',
                unsafe_allow_html=True,
            )
        with row[3]:
            st.markdown(
                f'<div style="margin:4px 0;">{status_badge(r.status)}</div>',
                unsafe_allow_html=True,
            )
        with row[4]:
            st.markdown(
                f'<p style="font-size:11px;color:#6B7280;margin:6px 0;">{r.sent_at}</p>',
                unsafe_allow_html=True,
            )
        with row[5]:
            v_color = "#15803D" if r.valid_rows > 0 else "#9CA3AF"
            st.markdown(
                f'<p style="font-size:12px;font-weight:700;color:{v_color};margin:6px 0;">'
                f'{r.valid_rows}</p>',
                unsafe_allow_html=True,
            )
        with row[6]:
            e_color = "#B91C1C" if r.invalid_rows > 0 else "#9CA3AF"
            st.markdown(
                f'<p style="font-size:12px;font-weight:700;color:{e_color};margin:6px 0;">'
                f'{r.invalid_rows}</p>',
                unsafe_allow_html=True,
            )

        # Menu de acoes via popover
        with row[7]:
            with st.popover("\u22ee", use_container_width=True):
                # Mini header
                st.markdown(
                    f'<p style="font-size:11px;font-weight:700;color:#002B5C;'
                    f'margin:0 0 8px;padding-bottom:6px;'
                    f'border-bottom:1px solid #F3F4F6;">'
                    f'{r.file_name[:30]}</p>',
                    unsafe_allow_html=True,
                )

                if r.status == "invalid":
                    st.button(
                        "Ver Erros",
                        key=f"pop_err_{r.upload_id}",
                        use_container_width=True,
                        on_click=_cb_ver_erros,
                        args=(r.upload_id,),
                    )

                if r.status in ("valid", "replaced", "canceled"):
                    st.button(
                        "Ver Detalhes",
                        key=f"pop_det_{r.upload_id}",
                        use_container_width=True,
                        on_click=_cb_ver_detalhes,
                        args=(r.upload_id,),
                    )

                if can_cancel(r):
                    st.button(
                        "Cancelar Envio",
                        key=f"pop_can_{r.upload_id}",
                        use_container_width=True,
                        on_click=_cb_cancelar,
                        args=(r.upload_id, supplier_id, user_email),
                    )

        # Separador de linha
        st.markdown(
            '<div style="border-top:1px solid #F3F4F6;margin:0;"></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    try:
        _render_impl()
    except Exception as exc:
        _logger.exception("Erro ao renderizar Meus Envios: %s", exc)
        st.error("Não foi possível carregar estas informações no momento. Tente novamente em alguns instantes.")


def _render_impl() -> None:
    supplier_id = st.session_state.get("supplier_id") or ""

    _render_page_header()

    # --- Banner de cancelamento (flash) ---
    just_cancelled_id = st.session_state.get("just_cancelled_upload_id")
    if just_cancelled_id:
        st.session_state.just_cancelled_upload_id = None
        st.success(f"Envio {just_cancelled_id} cancelado com sucesso.")

    if st.session_state.pop("_hist_cancel_error", None):
        st.error("Falha ao cancelar o envio. Verifique se o envio ainda esta ativo e tente novamente.")

    # --- Selectbox principal: Tipo de Relatorio ---
    enabled_types = get_enabled_report_types()
    type_options = ["Selecione..."] + enabled_types

    selected_type = st.selectbox(
        "Tipo de Relatório",
        options=type_options,
        index=0,
        key="hist_report_type",
    )

    if selected_type == "Selecione...":
        st.markdown(
            '<div style="padding:24px 0;font-size:14px;color:#6B7280;text-align:center;">'
            'Selecione um tipo de relatório para consultar seu histórico de envios.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # --- Carregar records do tipo ---
    all_records = get_supplier_uploads(supplier_id, include_mock=False)
    type_records = [r for r in all_records if r.report_type == selected_type]

    if not type_records:
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-top:12px;">'
            '<div class="kmt-alert-icon">&#128237;</div>'
            '<div>'
            f'<p class="kmt-alert-title">Nenhum envio de {selected_type} encontrado.</p>'
            '<p class="kmt-alert-body">'
            'Use <strong>Enviar Arquivo</strong> para registrar seu primeiro envio.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
        return

    # --- Cards ---
    _render_summary_cards(type_records)

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    # --- Filtro de status ---
    all_statuses = sorted({r.status for r in type_records})
    status_labels = [_STATUS_LABELS.get(s, s) for s in all_statuses]

    selected_status_label = st.selectbox(
        "Status do Envio",
        options=["Todos"] + status_labels,
        key="hist_status_filter",
    )

    if selected_status_label != "Todos":
        selected_status = _LABEL_TO_STATUS.get(selected_status_label)
        visible = [r for r in type_records if r.status == selected_status] if selected_status else type_records
    else:
        visible = type_records

    # --- Tabela com acoes por linha ---
    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="font-size:11px;color:#9CA3AF;margin:0 0 4px;">'
        f'{len(visible)} envio(s) de {selected_type}</p>',
        unsafe_allow_html=True,
    )
    _render_table_with_actions(visible)
