"""
streamlit_app.py

Entry point do Portal de Coleta e Validação de Forecast — Komatsu.
Gerencia o fluxo de login, estado de sessão e roteamento de páginas.
Toda lógica de UI é delegada aos módulos em components/.
"""

import sys
from pathlib import Path

# Garante que imports de components/, utils/, services/ funcionem
# independentemente do diretório onde o app é executado.
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from utils.streamlit_compat import safe_rerun
from components.layout import load_css, render_header, render_footer
from components.navigation import render_sidebar
from components.cards import metric_card, kpi_card, navy_card, render_cards_row
from components.badges import status_badge, version_badge
from pages.supplier_upload import render as render_upload
from pages.supplier_history import render as render_history
from pages.supplier_errors import render as render_errors
from services.upload_service import get_supplier_uploads, get_supplier_upload_batches
from pages.admin_suppliers import render as render_admin_suppliers
from pages.validated_data import render as render_validated_data
from pages.admin_upload_detail import render as render_upload_detail
from pages.admin_dashboard import render as render_admin_dashboard
from pages.admin_submission_windows import render as render_admin_windows
from utils.session_state import init_state as _init_session, get_session_uploads
from services.auth_service import do_admin_login

# --- Configuração da página (deve ser o primeiro comando Streamlit) ----------
st.set_page_config(
    page_title="Portal Komatsu | Coleta e Validação",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Inicialização do session_state ------------------------------------------
def _init_state() -> None:
    _init_session()  # delega para utils/session_state.py


def _do_login(role: str) -> None:
    """Login administrativo — usa auth_service para buscar dados do admin."""
    result = do_admin_login()
    if result.get("success"):
        st.session_state.login_mode = None
        st.session_state.selected_upload_id     = None
        st.session_state.detail_upload_id       = None
        st.session_state.errors_upload_id       = None
        st.session_state.selected_supplier_code = None
        st.session_state.origin_page            = None
        st.session_state.suppliers_form_mode    = None
        st.session_state.suppliers_edit_code    = None
    else:
        st.session_state.logged_in = True
        st.session_state.role = "admin"
        st.session_state.page = "admin_dashboard"
        st.session_state.user_name = "Administrador"
        st.session_state.user_email = "admin@komatsu.com.br"
        st.session_state.user_initials = "AP"
        st.session_state.login_mode = None


def _do_supplier_login(supplier) -> None:
    """
    Login simulado de fornecedor por e-mail.
    Identifica o fornecedor pelo e-mail selecionado e carrega seus dados
    em session_state. Sem autenticação real (MVP local).

    Limpa apenas estados temporários de navegação ao trocar de fornecedor.
    Dados funcionais (uploads, erros, forecasts) persistem durante toda a sessão.
    """
    st.session_state.logged_in       = True
    st.session_state.role            = "supplier"
    st.session_state.page            = "home"
    st.session_state.user_name       = supplier.name
    st.session_state.user_email      = supplier.email
    st.session_state.user_initials   = (supplier.name[0].upper() if supplier.name else "F")
    st.session_state.supplier_id     = supplier.code
    st.session_state.supplier_email  = supplier.email
    st.session_state.login_mode      = None
    # Limpa apenas estados temporários de navegação (dados funcionais persistem)
    st.session_state.selected_upload_id     = None
    st.session_state.detail_upload_id       = None
    st.session_state.errors_upload_id       = None
    st.session_state.origin_page            = None


# --- Tela de Login -----------------------------------------------------------
def _render_login() -> None:
    """Tela de login centralizada com cartão Komatsu."""
    if st.session_state.pop("_show_clear_msg", False):
        summary = st.session_state.pop("_clear_summary", "Dados limpos com sucesso.")
        st.success(summary)

    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown('<div class="kmt-login-card">', unsafe_allow_html=True)

        # Bloco navy com logo
        st.markdown(
            """
            <div class="kmt-login-header">
                <span class="kmt-login-logo">KOMATSU</span>
                <span class="kmt-login-subtitle">Portal de Coleta e Validação</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Corpo do cartão
        st.markdown('<div class="kmt-login-body">', unsafe_allow_html=True)

        login_mode = st.session_state.get("login_mode")

        if login_mode == "supplier":
            # ── Etapa 2: login por e-mail digitado ────────────────────────────
            st.markdown(
                '<p class="kmt-login-access-label">Acesso como Fornecedor</p>',
                unsafe_allow_html=True,
            )

            email_typed = st.text_input(
                "Digite seu e-mail:",
                placeholder="fornecedor@empresa.com",
                key="login_email_input",
                label_visibility="visible",
            )

            st.markdown('<div class="kmt-btn-yellow">', unsafe_allow_html=True)
            if st.button("Entrar", key="login_supplier_confirm",
                         use_container_width=True):
                from services.supplier_service import get_supplier_by_email
                email_clean = email_typed.strip().lower()

                if not email_clean:
                    st.error("Digite o e-mail para continuar.")
                else:
                    supplier = get_supplier_by_email(email_clean)
                    if supplier is None:
                        st.error(
                            "E-mail não cadastrado. "
                            "Verifique o endereço informado ou entre em contato "
                            "com a Komatsu."
                        )
                    elif supplier.status != "active":
                        st.warning(
                            "Fornecedor inativo. Entre em contato com a Komatsu "
                            "para regularizar o acesso."
                        )
                    else:
                        _do_supplier_login(supplier)
                        safe_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
            if st.button("← Voltar", key="login_back", use_container_width=True):
                st.session_state.login_mode = None
                safe_rerun()

        else:
            # ── Etapa 1: seleção de perfil ─────────────────────────────────────
            st.markdown(
                '<p class="kmt-login-access-label">Acesso ao Portal</p>',
                unsafe_allow_html=True,
            )

            # Botão Fornecedor
            st.markdown('<div class="kmt-btn-yellow">', unsafe_allow_html=True)
            if st.button("Entrar como Fornecedor", key="login_supplier",
                         use_container_width=True):
                st.session_state.login_mode = "supplier"
                safe_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

            # Botão Admin
            st.markdown('<div class="kmt-btn-secondary">', unsafe_allow_html=True)
            if st.button("Acesso Administrativo", key="login_admin",
                         use_container_width=True):
                _do_login("admin")
                safe_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # kmt-login-body

        # Rodapé do cartão
        st.markdown(
            """
            <div class="kmt-login-footer">
                © 2024 Komatsu | Uso Restrito<br>TI Operações
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)  # kmt-login-card


# --- Conteúdo: Fornecedor Home -----------------------------------------------

_STATUS_LABEL: dict[str, str] = {
    "valid":    "Válido/Ativo",
    "invalid":  "Inválido",
    "replaced": "Substituído",
    "canceled": "Cancelado",
}


def _render_supplier_home() -> None:
    """Dashboard do fornecedor — resumo dos uploads (Snowflake como fonte principal)."""

    supplier_id   = st.session_state.get("supplier_id") or ""
    supplier_name = st.session_state.get("user_name", "Fornecedor")

    # Fonte de verdade: Snowflake. Fallback: session_state.
    sf_recs = get_supplier_upload_batches(supplier_id)
    if sf_recs:
        recs = sf_recs
    else:
        recs = get_session_uploads(supplier_id)

    # Saudação
    st.markdown(
        '<div class="kmt-section">'
        f'<p class="kmt-section-title">Olá, {supplier_name}</p>'
        '<p class="kmt-section-subtitle">Seja bem-vindo ao portal de coleta de forecast.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Cards de resumo
    if not recs:
        render_cards_row([
            metric_card("Último Envio",       "Sem envio"),
            metric_card("Status Atual",       "Pendente"),
            metric_card("Versão Ativa",       "—"),
            metric_card("Linhas Processadas", "0"),
        ])
        st.markdown(
            '<div class="kmt-alert kmt-alert--info" style="margin-top:12px;margin-bottom:4px;">'
            '<div class="kmt-alert-icon">📭</div>'
            '<div>'
            '<p class="kmt-alert-title">Nenhum forecast enviado até o momento.</p>'
            '<p class="kmt-alert-body">'
            'Use o botão abaixo para enviar seu primeiro arquivo.'
            '</p></div></div>',
            unsafe_allow_html=True,
        )
    else:
        latest = recs[0]   # dict, mais recente primeiro
        active = next((r for r in recs if r.get("is_active")), None)

        status_label = _STATUS_LABEL.get(latest.get("status", ""), latest.get("status", "—"))
        versao_label = f"v.{active['version']}" if active else "—"
        linhas_total = latest.get("valid_rows", 0) + latest.get("invalid_rows", 0)
        erros_info   = f"{latest.get('invalid_rows', 0)} erros" if latest.get("invalid_rows", 0) > 0 else "0 erros"

        render_cards_row([
            metric_card("Último Envio",       latest.get("sent_at", "—")),
            metric_card("Status Atual",       status_label),
            metric_card("Versão Ativa",       versao_label),
            metric_card("Linhas Processadas", str(linhas_total), erros_info),
        ])

        # Tabela resumo do último envio
        _badge = status_badge(latest.get("status", ""))
        _ver = version_badge(latest.get("version", 0))
        _valid_c = (
            f'<span style="color:#15803D;font-weight:700;">{latest.get("valid_rows", 0)}</span>'
            if latest.get("valid_rows", 0) > 0 else
            '<span style="color:#9CA3AF;">0</span>'
        )
        _invalid_c = (
            f'<span style="color:#B91C1C;font-weight:700;">{latest.get("invalid_rows", 0)}</span>'
            if latest.get("invalid_rows", 0) > 0 else
            '<span style="color:#9CA3AF;">0</span>'
        )
        st.markdown(
            '<div class="kmt-table-container" style="margin-top:16px;">'
            '<div class="kmt-table-header">'
            '<span class="kmt-table-title">Último Envio</span>'
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
            '<tbody>'
            f'<tr class="kmt-table-row">'
            f'<td class="kmt-table-cell kmt-td-id">{latest.get("upload_id", "—")}</td>'
            f'<td class="kmt-table-cell" style="max-width:220px;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;" title="{latest.get("file_name", "")}">'
            f'{latest.get("file_name", "—")}</td>'
            f'<td class="kmt-table-cell kmt-td-period">{latest.get("period", "—")}</td>'
            f'<td class="kmt-table-cell kmt-td-center">{_ver}</td>'
            f'<td class="kmt-table-cell">{_badge}</td>'
            f'<td class="kmt-table-cell kmt-td-date">{latest.get("sent_at", "—")}</td>'
            f'<td class="kmt-table-cell kmt-td-center">{_valid_c}</td>'
            f'<td class="kmt-table-cell kmt-td-center">{_invalid_c}</td>'
            f'</tr>'
            '</tbody></table></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)

    # Ações rápidas + aviso de privacidade
    col_main, col_side = st.columns([2, 1])

    with col_main:
        # Título da seção sem tags HTML abertas/fechadas em chamadas separadas
        st.markdown(
            '<p class="kmt-card-label" style="margin:0 0 10px;">Ações Rápidas</p>',
            unsafe_allow_html=True,
        )
        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button("📤  Enviar Arquivo", key="home_btn_upload", use_container_width=True):
                st.session_state.page = "upload"
                safe_rerun()
        with btn2:
            if st.button("Ir para Templates e Envio", key="home_btn_template", use_container_width=True):
                st.session_state.page = "upload"
                safe_rerun()
        with btn3:
            if st.button("📋  Ver Meus Envios", key="home_btn_history", use_container_width=True):
                st.session_state.page = "history"
                safe_rerun()

    with col_side:
        st.markdown(
            navy_card(
                title="Aviso de Privacidade",
                body=(
                    "Você visualiza apenas os envios e históricos "
                    f"relacionados ao seu fornecedor ({supplier_name})."
                ),
                version="v1.2.0-MVP",
            ),
            unsafe_allow_html=True,
        )


# --- Roteador de páginas -----------------------------------------------------
_PAGE_TITLES = {
    "home":                 "Dashboard do Fornecedor",
    "upload":               "Submeter Novo Forecast",
    "history":              "Meus Envios",
    "errors":               "Erros / Relatório de Correção",
    "admin_dashboard":      "Painel Administrativo de Coleta",
    "admin_windows":        "Janelas de Envio",
    "validated_data":       "Forecasts Validados",
    "admin_suppliers":      "Gestão de Fornecedores",
    "admin_upload_detail":  "Detalhe do Envio",
}


def _render_placeholder(page: str) -> None:
    """Placeholder para telas ainda não implementadas."""
    title = _PAGE_TITLES.get(page, page)
    st.markdown(
        f"""
        <div class="kmt-alert kmt-alert--info" style="margin-top:32px;">
            <div class="kmt-alert-icon">🚧</div>
            <div>
                <p class="kmt-alert-title">{title}</p>
                <p class="kmt-alert-body">
                    Esta tela será implementada na próxima etapa.
                    Navegue pelo menu lateral para explorar o layout.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- App principal -----------------------------------------------------------
def main() -> None:
    _init_state()
    load_css()

    # Tela de login (sem sidebar)
    if not st.session_state.logged_in:
        _render_login()
        return

    # Layout autenticado
    with st.sidebar:
        render_sidebar(
            role=st.session_state.role,
            current_page=st.session_state.page,
        )
        # ── Ferramenta de reset (visível apenas para admin em ambiente dev/test) ──
        from utils.constants import APP_ENV
        if st.session_state.get("role") == "admin" and APP_ENV in ("dev", "test", "local"):
            st.markdown("---")
            st.markdown(
                '<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.06em;color:#9CA3AF;margin:0 0 6px;">Dev / Teste</p>',
                unsafe_allow_html=True,
            )

            confirm_clear = st.checkbox(
                "Confirmo que quero apagar dados de teste",
                key="chk_confirm_clear",
                value=False,
            )

            if st.button(
                "🗑  Limpar dados de teste",
                key="btn_reset_local",
                use_container_width=True,
                help="Remove dados criados em teste do Snowflake e limpa session_state.",
                disabled=not confirm_clear,
            ):
                from services.dev_tools_service import clear_dev_data
                from utils.session_state import reset_local_data

                # Limpar Snowflake
                cleanup_result = clear_dev_data()

                # Limpar session_state
                reset_local_data()

                # Exibir resumo
                if cleanup_result["success"]:
                    deleted = cleanup_result["deleted"]
                    summary_lines = [
                        f"- **{table}**: {count} removidos"
                        for table, count in deleted.items()
                        if isinstance(count, int) and count > 0
                    ]
                    if summary_lines:
                        st.session_state["_clear_summary"] = (
                            "Dados de teste removidos:\n\n" + "\n".join(summary_lines)
                        )
                    else:
                        st.session_state["_clear_summary"] = (
                            "Nenhum dado de teste encontrado para remover."
                        )
                else:
                    errors = cleanup_result["errors"]
                    st.session_state["_clear_summary"] = (
                        "Limpeza com erros:\n\n" + "\n".join(f"- {e}" for e in errors)
                    )

                st.session_state["_show_clear_msg"] = True
                safe_rerun()

    page = st.session_state.page
    title = _PAGE_TITLES.get(page, "Portal Komatsu")

    render_header(
        title=title,
        user_name=st.session_state.user_name,
        user_email=st.session_state.user_email,
        user_initials=st.session_state.user_initials,
    )

    st.markdown('<div class="kmt-main-content">', unsafe_allow_html=True)

    # Roteamento de páginas com verificação de perfil
    role = st.session_state.role

    # Páginas exclusivas de fornecedor
    if page == "home" and role == "supplier":
        _render_supplier_home()
    elif page == "upload" and role == "supplier":
        render_upload()
    elif page == "history" and role == "supplier":
        render_history()
    elif page == "errors" and role == "supplier":
        render_errors()

    # Redirecionamento: admin vai direto ao painel
    elif page == "home" and role == "admin":
        st.session_state.page = "admin_dashboard"
        safe_rerun()

    # Páginas exclusivas de admin
    elif page == "admin_dashboard" and role == "admin":
        render_admin_dashboard()
    elif page == "admin_windows" and role == "admin":
        render_admin_windows()
    elif page == "admin_suppliers" and role == "admin":
        render_admin_suppliers()
    elif page == "validated_data" and role == "admin":
        render_validated_data()
    elif page == "admin_upload_detail" and role == "admin":
        render_upload_detail()

    # Erros de validação: admin pode consultar erros de qualquer upload inválido
    elif page == "errors" and role == "admin":
        render_errors()

    # Detalhe do envio: compartilhado (fornecedor acessa via histórico)
    elif page == "admin_upload_detail" and role == "supplier":
        render_upload_detail()

    # Acesso não autorizado — fornecedor tentando acessar página admin
    elif role == "supplier":
        st.markdown(
            """
            <div class="kmt-alert kmt-alert--info" style="margin-top:32px;">
                <div class="kmt-alert-icon">🔒</div>
                <div>
                    <p class="kmt-alert-title">Acesso não permitido para este perfil.</p>
                    <p class="kmt-alert-body">
                        Esta área é restrita ao perfil administrativo.
                        Use o menu lateral para navegar pelas suas telas.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Acesso não autorizado — admin tentando acessar página de fornecedor
    else:
        st.session_state.page = "admin_dashboard"
        safe_rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    render_footer()


if __name__ == "__main__" or True:
    main()
