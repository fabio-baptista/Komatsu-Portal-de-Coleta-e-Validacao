"""
supplier_errors.py

Tela de detalhamento de erros de um envio específico.
Exibe a lista de erros encontrados na validação, com linha, coluna e descrição,
e permite o download do relatório de erros em .csv.
"""

import pandas as pd
import streamlit as st

from components.badges import status_badge
from components.cards import metric_card, render_cards_row
from components.tables import errors_table
from services.upload_service import get_validation_errors
from utils.session_state import get_origin_page, get_session_errors
from utils.file_reader import build_error_report
from utils.logger import get_logger
from services.mock_data_service import get_mock_validation_errors, get_mock_upload_by_id
from utils.streamlit_compat import safe_rerun

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Resolução dinâmica do contexto (upload_id vem do session_state)
# ---------------------------------------------------------------------------


def _get_upload_context(upload_id: str) -> dict:
    """
    Retorna o contexto do upload para exibição no card.
    Verifica uploads da sessão primeiro, depois mock_data_service.
    """
    # Verificar uploads registrados na sessão
    session_uploads = st.session_state.get("session_uploads", [])
    for u in session_uploads:
        if u.get("upload_id") == upload_id:
            return {
                "upload_id": u["upload_id"],
                "file_name": u["file_name"],
                "supplier":  u.get("supplier_name", "—"),
                "period":    u.get("period", "—"),
                "status":    u["status"],
            }
    # Fallback para dados mock
    raw = get_mock_upload_by_id(upload_id)
    if raw:
        return {
            "upload_id": raw["upload_id"],
            "file_name": raw["file_name"],
            "supplier":  raw["supplier_name"],
            "period":    raw["period"],
            "status":    raw["status"],
        }
    return {
        "upload_id": upload_id,
        "file_name": "—",
        "supplier":  "—",
        "period":    "—",
        "status":    "invalid",
    }


def _get_errors_df(upload_id: str) -> pd.DataFrame:
    """
    Retorna DataFrame de erros para o upload_id informado.
    Prioridade: Snowflake (fonte de verdade) > session_state (fallback) > mock.
    """
    # 1. Fonte de verdade: Snowflake CONTROL.VALIDATION_ERRORS
    sf_errors = get_validation_errors(upload_id)
    if sf_errors:
        _logger.info(
            "Erros carregados do Snowflake: upload_id=%s, total=%d",
            upload_id, len(sf_errors),
        )
        return pd.DataFrame(sf_errors)

    # 2. Fallback temporário: session_state (para uploads da sessão atual
    #    caso Snowflake não retorne — ex: gravação falhou parcialmente)
    session_errs = get_session_errors(upload_id)
    if session_errs is not None:
        _logger.warning(
            "Fallback para session_state: upload_id=%s, total=%d. "
            "Erros não encontrados no Snowflake.",
            upload_id, len(session_errs),
        )
        return pd.DataFrame(session_errs)

    # 3. Fallback para dados mock (modo demo)
    mock_errs = get_mock_validation_errors(upload_id)
    if mock_errs:
        _logger.info(
            "Erros carregados do mock: upload_id=%s, total=%d",
            upload_id, len(mock_errs),
        )
        return pd.DataFrame(mock_errs)

    # 4. Nenhum erro encontrado em nenhuma fonte
    _logger.info(
        "Nenhum erro encontrado para upload_id=%s", upload_id,
    )
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Seções da tela
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    st.markdown(
        """
        <div class="kmt-section">
            <p class="kmt-section-title">Erros de Validação</p>
            <p class="kmt-section-subtitle">
                Consulte as inconsistências encontradas no arquivo
                e baixe o relatório de correção.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_upload_context(ctx: dict, n_errors: int) -> None:
    """Card de contexto do upload com metadados e status."""
    badge = status_badge(ctx["status"])

    st.markdown(
        f"""
        <div class="kmt-card" style="margin-bottom:20px;">
            <p class="kmt-card-label" style="margin-bottom:14px;">Contexto do Envio</p>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);
                        gap:12px 24px;">
                <div>
                    <p style="font-size:10px;font-weight:700;color:#9CA3AF;
                              text-transform:uppercase;letter-spacing:0.1em;margin:0 0 3px;">
                        Upload ID
                    </p>
                    <p style="font-family:monospace;font-weight:700;
                              color:#2563EB;margin:0;font-size:14px;">
                        {ctx['upload_id']}
                    </p>
                </div>
                <div>
                    <p style="font-size:10px;font-weight:700;color:#9CA3AF;
                              text-transform:uppercase;letter-spacing:0.1em;margin:0 0 3px;">
                        Arquivo
                    </p>
                    <p style="font-size:13px;font-weight:600;color:#002B5C;
                              margin:0;word-break:break-all;">
                        {ctx['file_name']}
                    </p>
                </div>
                <div>
                    <p style="font-size:10px;font-weight:700;color:#9CA3AF;
                              text-transform:uppercase;letter-spacing:0.1em;margin:0 0 3px;">
                        Fornecedor
                    </p>
                    <p style="font-size:13px;font-weight:600;color:#002B5C;margin:0;">
                        {ctx['supplier']}
                    </p>
                </div>
                <div>
                    <p style="font-size:10px;font-weight:700;color:#9CA3AF;
                              text-transform:uppercase;letter-spacing:0.1em;margin:0 0 3px;">
                        Período
                    </p>
                    <p style="font-size:13px;font-weight:600;color:#002B5C;margin:0;">
                        {ctx['period']}
                    </p>
                </div>
                <div>
                    <p style="font-size:10px;font-weight:700;color:#9CA3AF;
                              text-transform:uppercase;letter-spacing:0.1em;margin:0 0 3px;">
                        Status
                    </p>
                    <p style="margin:0;">{badge}</p>
                </div>
                <div>
                    <p style="font-size:10px;font-weight:700;color:#9CA3AF;
                              text-transform:uppercase;letter-spacing:0.1em;margin:0 0 3px;">
                        Total de Erros
                    </p>
                    <p style="font-size:18px;font-weight:700;color:#B91C1C;margin:0;">
                        {n_errors}
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_error_alert() -> None:
    """Alerta visual em destaque."""
    st.markdown(
        """
        <div class="kmt-alert kmt-alert--error">
            <div class="kmt-alert-icon">❌</div>
            <div>
                <p class="kmt-alert-title">Arquivo Inválido</p>
                <p class="kmt-alert-body">
                    Corrija os erros na planilha original e realize um novo envio.
                    Não é possível editar os dados diretamente no portal.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_cards(errors_df: pd.DataFrame) -> None:
    """Cards com contagem de erros por tipo."""
    total      = len(errors_df)
    obrigatorio = (errors_df["erro"] == "Campo obrigatório").sum()
    tipo        = (errors_df["erro"] == "Tipo inválido").sum()
    outros      = total - int(obrigatorio) - int(tipo)

    render_cards_row([
        metric_card("Total de Erros",       str(total)),
        metric_card("Campos Obrigatórios",  str(obrigatorio)),
        metric_card("Tipo de Dado Inválido", str(tipo)),
        metric_card("Outros",               str(outros)),
    ])


def _render_download_and_note(errors_df: pd.DataFrame, ctx: dict) -> None:
    """Botão de download do relatório e observação sobre preservação do original."""
    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    col_dl, col_back, _ = st.columns([2, 2, 4])

    with col_dl:
        report_data, report_name, report_mime = build_error_report(
            errors_df, ctx["upload_id"]
        )
        st.download_button(
            label="⬇  Baixar relatório de correção",
            data=report_data,
            file_name=report_name,
            mime=report_mime,
            use_container_width=True,
        )

    with col_back:
        # Resolve a página de retorno: histórico para fornecedor, painel para admin
        role = st.session_state.get("role", "supplier")
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

    st.markdown(
        """
        <div style="margin-top:20px;padding:10px 16px;background:#F9FAFB;
                    border-left:3px solid #E5E7EB;border-radius:4px;">
            <p style="font-size:12px;color:#374151;margin:0 0 4px;font-weight:600;">
                Baixe o relatório, corrija a planilha original e envie novamente.
            </p>
            <p style="font-size:11px;color:#9CA3AF;margin:0;">
                O arquivo original enviado é preservado sem alterações.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """
    Renderiza a tela de erros de validação.
    Chamado por streamlit_app.py quando page == 'errors'.
    O upload_id é lido do session_state (definido por navigate_to).
    """
    _render_page_header()

    upload_id = st.session_state.get("errors_upload_id")

    # Nenhum upload selecionado — mensagem amigável
    if not upload_id:
        st.markdown(
            """
            <div class="kmt-alert kmt-alert--info" style="margin-top:24px;">
                <div class="kmt-alert-icon">ℹ</div>
                <div>
                    <p class="kmt-alert-title">Nenhum envio inválido selecionado</p>
                    <p class="kmt-alert-body">
                        Acesse <strong>Meus Envios</strong> e selecione um arquivo com erro para visualizar o relatório de correção.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
        col_back, _ = st.columns([2, 4])
        with col_back:
            if st.button("← Voltar para Meus Envios", key="btn_back_no_errors_id", use_container_width=True):
                st.session_state.page = "history"
                safe_rerun()
        return

    ctx       = _get_upload_context(upload_id)
    errors_df = _get_errors_df(upload_id)
    n_errors  = len(errors_df)

    _render_upload_context(ctx, n_errors)

    # Nenhum erro encontrado para este upload
    if n_errors == 0:
        st.markdown(
            """
            <div class="kmt-alert kmt-alert--info" style="margin-top:24px;">
                <div class="kmt-alert-icon">ℹ</div>
                <div>
                    <p class="kmt-alert-title">Nenhum erro encontrado para este envio</p>
                    <p class="kmt-alert-body">
                        Não há erros de validação registrados para este arquivo.
                        Caso tenha enviado um novo arquivo corrigido, os erros do envio anterior
                        não se aplicam mais.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    _render_error_alert()

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    _render_summary_cards(errors_df)

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)

    # Tabela de erros (reutiliza componente de tables.py)
    st.markdown(errors_table(errors_df), unsafe_allow_html=True)

    _render_download_and_note(errors_df, ctx)
