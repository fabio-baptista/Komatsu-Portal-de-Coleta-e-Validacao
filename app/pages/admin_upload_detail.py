"""
admin_upload_detail.py

Tela de detalhe de um envio específico, acessada pelo admin.
Exibe rastreabilidade operacional do upload: identificação, resumo de linhas,
timeline de processamento, metadados e resumo de validação.
Dados fictícios locais — sem conexão com Snowflake.
"""

import streamlit as st

from components.badges import status_badge, version_badge
from components.cards import metric_card, render_cards_row
from services.upload_service import UploadDetail, get_upload_detail
from utils.session_state import get_origin_page
from utils.streamlit_compat import safe_rerun


# ---------------------------------------------------------------------------
# Seções da tela
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        '<div class="kmt-section">'
        '<p class="kmt-section-title">Detalhe do Envio</p>'
        '<p class="kmt-section-subtitle">'
        'Consulte as informações do arquivo enviado, status de validação '
        'e histórico operacional.'
        '</p></div>',
        unsafe_allow_html=True,
    )


def _render_identification_block(d: UploadDetail) -> None:
    """
    Identificação do upload usando st.columns() nativos do Streamlit.
    Evita f-string HTML monolítico que pode causar renderização incorreta
    em determinadas configurações de tema/versão do Streamlit.
    """
    badge_html   = status_badge(d.status)
    version_html = version_badge(d.version)

    def _field(label: str, value: str, mono: bool = False) -> str:
        color = "#002B5C" if mono else "#374151"
        family = "font-family:monospace;" if mono else ""
        return (
            f'<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.08em;color:#9CA3AF;margin:0 0 3px;">{label}</p>'
            f'<p style="font-size:13px;font-weight:600;color:{color};'
            f'{family}margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"'
            f' title="{value}">{value}</p>'
        )

    st.markdown(
        '<p class="kmt-card-label" style="margin-bottom:10px;">Identificação do Upload</p>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_field("Upload ID", d.upload_id, mono=True), unsafe_allow_html=True)
    with c2:
        st.markdown(_field("Fornecedor", d.supplier_name), unsafe_allow_html=True)
    with c3:
        st.markdown(_field("Arquivo", d.file_name, mono=True), unsafe_allow_html=True)

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(_field("Tipo de Relatório", d.report_type), unsafe_allow_html=True)
    with c5:
        st.markdown(
            f'<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.08em;color:#9CA3AF;margin:0 0 3px;">Período</p>'
            f'<p style="font-size:14px;font-weight:700;color:#2563EB;'
            f'font-family:monospace;margin:0;">{d.period}</p>',
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            '<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.08em;color:#9CA3AF;margin:0 0 4px;">Versão</p>',
            unsafe_allow_html=True,
        )
        st.markdown(version_html, unsafe_allow_html=True)

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    c7, c8, c9 = st.columns(3)
    with c7:
        st.markdown(
            '<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.08em;color:#9CA3AF;margin:0 0 4px;">Status</p>',
            unsafe_allow_html=True,
        )
        st.markdown(badge_html, unsafe_allow_html=True)
    with c8:
        st.markdown(_field("Enviado por", d.uploaded_by, mono=True), unsafe_allow_html=True)
    with c9:
        st.markdown(_field("Data de Envio", d.sent_at), unsafe_allow_html=True)

    st.markdown(
        '<hr style="margin:14px 0 4px;border:none;border-top:1px solid #F3F4F6;">',
        unsafe_allow_html=True,
    )


def _render_summary_cards(d: UploadDetail) -> None:
    """Cards de resumo de linhas. Admin vê 'Status do Processamento' em vez de camada técnica."""
    role = st.session_state.get("role", "admin")
    cards = [
        metric_card("Total de Linhas",  str(d.total_rows)),
        metric_card("Linhas Válidas",   str(d.valid_rows)),
        metric_card("Linhas com Erro",  str(d.invalid_rows)),
    ]
    if role == "admin":
        _PROC_STATUS = {
            "valid":    "Processado",
            "invalid":  "Processado com Erros",
            "pending":  "Aguardando",
            "canceled": "Cancelado",
            "replaced": "Substituído",
        }
        proc_label = _PROC_STATUS.get(d.status, d.status.capitalize())
        cards.append(metric_card("Status do Processamento", proc_label))
    render_cards_row(cards)


def _render_timeline(d: UploadDetail) -> None:
    """Timeline visual de processamento com etapas e timestamps."""
    steps_html = ""
    n = len(d.timeline)
    for i, step in enumerate(d.timeline):
        is_last = i == n - 1
        dot_bg  = "#002B5C" if step.completed else "#E5E7EB"
        dot_color = "#FFCD00" if step.completed else "#9CA3AF"
        label_color = "#002B5C" if step.completed else "#9CA3AF"
        ts_html = (
            f'<p style="font-size:10px;color:#9CA3AF;margin:4px 0 0;'
            f'font-family:monospace;">{step.timestamp}</p>'
            if step.timestamp else ""
        )
        connector = (
            ""
            if is_last
            else (
                '<div style="flex:1;height:2px;background:'
                + ("#002B5C" if step.completed else "#E5E7EB")
                + ';margin-top:-20px;"></div>'
            )
        )
        steps_html += (
            '<div style="display:flex;flex-direction:column;align-items:center;flex:1;">'
            f'<div style="width:36px;height:36px;border-radius:50%;background:{dot_bg};'
            'display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">'
            f'<span style="color:{dot_color};font-weight:700;">{"✓" if step.completed else "○"}</span>'
            '</div>'
            f'<p style="font-size:12px;font-weight:600;color:{label_color};margin:8px 0 0;text-align:center;">{step.label}</p>'
            f'{ts_html}'
            '</div>'
            + ("" if is_last else f'<div style="flex:1;height:2px;background:{"#002B5C" if step.completed else "#E5E7EB"};margin:18px -8px 0;align-self:flex-start;"></div>')
        )

    st.markdown(
        '<div class="kmt-card" style="padding:20px 24px;">'
        '<p class="kmt-card-label" style="margin-bottom:16px;">Timeline de Processamento</p>'
        f'<div style="display:flex;align-items:flex-start;gap:0;padding:8px 16px;">{steps_html}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_metadata_table(d: UploadDetail) -> None:
    """
    Tabela de metadados do envio.
    Admin vê campos técnicos em snake_case.
    Fornecedor vê campos amigáveis em português.
    """
    role = st.session_state.get("role", "admin")

    if role == "supplier":
        rows_data = [
            ("Arquivo",          d.file_name),
            ("Período",          d.period),
            ("Versão",           str(d.version)),
            ("Status",           d.status.upper()),
            ("Enviado por",      d.uploaded_by),
            ("Data de Envio",    d.sent_at),
            ("Total de Linhas",  str(d.total_rows)),
            ("Linhas Válidas",   str(d.valid_rows)),
            ("Linhas com Erro",  str(d.invalid_rows)),
        ]
        table_title = "Informações do Envio"
    else:
        _PROC_LABELS = {
            "valid":    "Processado",
            "invalid":  "Processado com Erros",
            "pending":  "Aguardando",
            "canceled": "Cancelado",
            "replaced": "Substituído",
        }
        rows_data = [
            ("Upload ID",              d.upload_id),
            ("Fornecedor",             d.supplier_name),
            ("Arquivo",                d.file_name),
            ("Período",                d.period),
            ("Versão",                 str(d.version)),
            ("Status",                 d.status.upper()),
            ("Enviado por",            d.uploaded_by),
            ("Data de Envio",          d.sent_at),
            ("Total de Linhas",        str(d.total_rows)),
            ("Linhas Válidas",         str(d.valid_rows)),
            ("Linhas com Erro",        str(d.invalid_rows)),
            ("Status do Processamento",_PROC_LABELS.get(d.status, d.status.capitalize())),
        ]
        table_title = "Informações do Envio"
    rows_html = ""
    for campo, valor in rows_data:
        rows_html += (
            '<tr class="kmt-table-row">'
            f'<td class="kmt-table-cell" style="font-family:monospace;font-weight:600;color:#002B5C;font-size:12px;">{campo}</td>'
            f'<td class="kmt-table-cell" style="font-size:12px;color:#374151;">{valor}</td>'
            '</tr>'
        )

    st.markdown(
        '<div class="kmt-table-container">'
        '<div class="kmt-table-header">'
        f'<span class="kmt-table-title">{table_title}</span>'
        '</div>'
        '<div class="kmt-table-scroll">'
        '<table class="kmt-table">'
        '<thead><tr class="kmt-thead-row">'
        '<th class="kmt-th">Campo</th>'
        '<th class="kmt-th">Valor</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div></div>',
        unsafe_allow_html=True,
    )


def _render_validation_table(d: UploadDetail) -> None:
    """Tabela de resumo de validação do envio."""
    rows_html = ""
    for chk in d.validation_checks:
        result_color = "#15803D" if chk.result == "OK" else "#B91C1C"
        result_bg    = "#DCFCE7" if chk.result == "OK" else "#FEE2E2"
        rows_html += (
            '<tr class="kmt-table-row">'
            f'<td class="kmt-table-cell" style="font-weight:600;font-size:13px;color:#374151;">{chk.check}</td>'
            f'<td class="kmt-table-cell">'
            f'<span style="display:inline-block;padding:3px 10px;border-radius:9999px;font-size:11px;'
            f'font-weight:700;background:{result_bg};color:{result_color};">{chk.result}</span></td>'
            f'<td class="kmt-table-cell" style="font-size:12px;color:#6B7280;font-style:italic;">{chk.observation}</td>'
            '</tr>'
        )

    st.markdown(
        '<div class="kmt-table-container">'
        '<div class="kmt-table-header">'
        '<span class="kmt-table-title">Resumo de Validação</span>'
        '</div>'
        '<div class="kmt-table-scroll">'
        '<table class="kmt-table">'
        '<thead><tr class="kmt-thead-row">'
        '<th class="kmt-th">Validação</th>'
        '<th class="kmt-th">Resultado</th>'
        '<th class="kmt-th">Observação</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div></div>',
        unsafe_allow_html=True,
    )


def _render_actions(detail: UploadDetail) -> None:
    """
    Ações do envio.
    - Cancelar envio: visível APENAS para role == "supplier" quando can_cancel() == True.
      Admin acompanha status mas não executa cancelamento em nome do fornecedor.
    - Reprocessar: removido do MVP. Novo envio substitui versão anterior.
    - Voltar: navega para a origem.
    - Baixar relatório: download do resumo em CSV.
    """
    from services.upload_service import can_cancel, UploadRecord, persist_cancel_upload
    from utils.session_state import deactivate_validated_forecast

    role = st.session_state.get("role", "admin")

    # Cancelamento: apenas fornecedor, dentro da janela, upload válido ativo
    temp_record = UploadRecord(
        upload_id=    detail.upload_id,
        file_name=    detail.file_name,
        period=       detail.period,
        version=      detail.version,
        status=       detail.status,
        sent_at=      detail.sent_at,
        valid_rows=   detail.valid_rows,
        invalid_rows= detail.invalid_rows,
        supplier_id=  detail.supplier_id,
        is_active=    detail.is_active,
    )
    show_cancel = (role == "supplier" and can_cancel(temp_record))

    st.markdown(
        '<div class="kmt-card" style="padding:16px 20px;">'
        '<p class="kmt-card-label" style="margin-bottom:12px;">Ações</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_back, col_download, col_cancel = st.columns([2, 2, 4])

    with col_back:
        fallback = "history" if role == "supplier" else "admin_dashboard"
        back_page = get_origin_page(fallback=fallback)
        back_labels = {
            "history":         "← Voltar para Meus Envios",
            "admin_dashboard": "← Voltar ao Painel",
            "admin_suppliers": "← Voltar a Fornecedores",
        }
        back_label = back_labels.get(back_page, "← Voltar")
        if st.button(back_label, key="btn_back_history", use_container_width=True):
            st.session_state.page = back_page
            safe_rerun()

    with col_download:
        report_text = (
            "Upload ID,Fornecedor,Arquivo,Período,Versão,Status,Enviado por,Data\n"
            f"{detail.upload_id},{detail.supplier_name},{detail.file_name},"
            f"{detail.period},{detail.version},{detail.status.upper()},"
            f"{detail.uploaded_by},{detail.sent_at}\n"
        )
        st.download_button(
            label="⬇  Baixar relatório do envio",
            data=report_text.encode("utf-8"),
            file_name=f"relatorio_{detail.upload_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_cancel:
        if show_cancel:
            if st.button(
                "✕  Cancelar envio",
                key="btn_cancel_detail",
                use_container_width=True,
            ):
                user_email = st.session_state.get("user_email", "—")
                supplier_id = st.session_state.get("supplier_id") or detail.supplier_id
                success = persist_cancel_upload(
                    upload_id=detail.upload_id,
                    supplier_id=supplier_id,
                    cancelled_by=user_email,
                )
                if success:
                    deactivate_validated_forecast(detail.upload_id)
                    st.session_state.just_cancelled_upload_id = detail.upload_id
                else:
                    st.error(
                        "Falha ao cancelar o envio no Snowflake. "
                        "Verifique se o envio ainda está ativo e tente novamente."
                    )
                fallback = "history" if role == "supplier" else "admin_dashboard"
                st.session_state.page = get_origin_page(fallback=fallback)
                safe_rerun()


def _render_disclaimer() -> None:
    """Observação discreta sobre o escopo da tela."""
    st.markdown(
        '<div style="margin-top:16px;padding:10px 16px;background:#F9FAFB;'
        'border-left:3px solid #E5E7EB;border-radius:4px;">'
        '<p style="font-size:11px;color:#9CA3AF;margin:0;font-family:monospace;">'
        'ℹ&nbsp; Esta tela não altera os dados. Ela demonstra a rastreabilidade '
        'do upload, status de validação e destino final do processamento.'
        '</p></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """
    Renderiza a tela de detalhe de envio.
    Chamado por streamlit_app.py quando page == 'admin_upload_detail'.
    """
    try:
        _render_impl()
    except Exception as exc:
        from utils.logger import get_logger
        get_logger(__name__).exception("Erro ao renderizar Detalhe do Envio: %s", exc)
        st.error("Não foi possível carregar estas informações no momento. Tente novamente em alguns instantes.")


def _render_impl() -> None:
    """Implementação interna da tela de detalhe."""
    upload_id = st.session_state.get("detail_upload_id")

    _render_page_header()

    # Nenhum upload selecionado
    if not upload_id:
        role = st.session_state.get("role", "admin")
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-top:24px;">'
            '<div class="kmt-alert-icon">ℹ</div>'
            '<div>'
            '<p class="kmt-alert-title">Nenhum envio selecionado</p>'
            '<p class="kmt-alert-body">'
            'Acesse o painel ou a lista de fornecedores para selecionar '
            'um envio e visualizar seus detalhes.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
        col_back, _ = st.columns([2, 4])
        with col_back:
            if role == "supplier":
                if st.button("← Voltar para Meus Envios", key="btn_back_no_id",
                             use_container_width=True):
                    st.session_state.page = "history"
                    safe_rerun()
            else:
                if st.button("← Voltar ao Painel", key="btn_back_no_id",
                             use_container_width=True):
                    st.session_state.page = "admin_dashboard"
                    safe_rerun()
        return

    detail = get_upload_detail(upload_id)

    if detail is None:
        role = st.session_state.get("role", "admin")
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-top:24px;">'
            '<div class="kmt-alert-icon">⚠</div>'
            '<div>'
            '<p class="kmt-alert-title">Envio não encontrado</p>'
            '<p class="kmt-alert-body">'
            f'Não foi possível carregar os dados do envio <strong>{upload_id}</strong>.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
        col_back, _ = st.columns([2, 4])
        with col_back:
            if role == "supplier":
                if st.button("← Voltar para Meus Envios", key="btn_back_not_found",
                             use_container_width=True):
                    st.session_state.page = "history"
                    safe_rerun()
            else:
                if st.button("← Voltar ao Painel", key="btn_back_not_found",
                             use_container_width=True):
                    st.session_state.page = "admin_dashboard"
                    safe_rerun()
        return

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    _render_identification_block(detail)

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)
    _render_summary_cards(detail)

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)
    if detail.timeline:
        _render_timeline(detail)
        st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)

    col_meta, col_valid = st.columns(2)
    with col_meta:
        _render_metadata_table(detail)
    with col_valid:
        if detail.validation_checks:
            _render_validation_table(detail)

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)
    _render_actions(detail)
    _render_disclaimer()
