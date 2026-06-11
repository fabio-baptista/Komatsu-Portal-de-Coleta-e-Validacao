"""
admin_suppliers.py

Tela de gestão de fornecedores — estrutura CRUD administrativa.

Layout:
  1. Header: título/subtítulo à esquerda + "＋ Cadastrar" à direita
  2. Formulário inline (add/edit) — abaixo do header quando ativo
  3. Cards KPI compactos
  4. Linha de filtros sem wrapper pesado
  5. Tabela com coluna "⋮" por linha
  6. Área contextual compacta após clicar ⋮

Dados: CONTROL.SUPPLIERS via Snowflake (fonte de verdade).
"""

import streamlit as st

from components.badges import status_badge
from components.cards import metric_card, render_cards_row
from services.mock_data_service import get_current_open_window
from services.supplier_service import (
    SupplierRecord,
    create_supplier,
    get_all_suppliers,
    get_next_supplier_code,
    get_supplier_by_code,
    get_summary,
    update_supplier,
    update_supplier_status,
)
from services.upload_service import get_admin_status_rows
from utils.session_state import (
    navigate_to,
)
from utils.streamlit_compat import safe_rerun

# Limite de fornecedores exibidos por vez (sem paginação completa)
_DISPLAY_LIMIT = 50

# Larguras das colunas da tabela
# Fornecedor | E-mail | Código | Status | Último Envio | Status Período | Ações
_COLS = [2.5, 2.5, 1.2, 1.2, 1.5, 1.5, 0.8]


# ---------------------------------------------------------------------------
# Callbacks de ações do popover (on_click — garante fechamento do menu)
# ---------------------------------------------------------------------------

def _cb_inativar(code: str, name: str) -> None:
    supplier = get_supplier_by_code(code)
    if supplier and update_supplier_status(supplier.supplier_id, "inactive"):
        st.session_state.supplier_status_msg = (
            f"Distribuidor **{name}** inativado com sucesso."
        )
    else:
        st.session_state.supplier_status_msg = (
            f"Erro ao inativar distribuidor **{name}**."
        )
    if st.session_state.get("selected_supplier_code") == code:
        st.session_state.selected_supplier_code = None
        st.session_state.supplier_show_detail   = False


def _cb_ativar(code: str, name: str) -> None:
    supplier = get_supplier_by_code(code)
    if supplier and update_supplier_status(supplier.supplier_id, "active"):
        st.session_state.supplier_status_msg = (
            f"Distribuidor **{name}** ativado com sucesso."
        )
    else:
        st.session_state.supplier_status_msg = (
            f"Erro ao ativar distribuidor **{name}**."
        )


def _cb_ver_detalhe(code: str) -> None:
    st.session_state.selected_supplier_code = code
    st.session_state.supplier_show_detail   = True
    st.session_state.suppliers_form_mode    = None


def _cb_editar(code: str) -> None:
    st.session_state.suppliers_form_mode  = "edit"
    st.session_state.suppliers_edit_code  = code
    st.session_state.supplier_show_detail = False


def _cb_ver_erros(upload_id: str) -> None:
    navigate_to("errors", upload_id=upload_id, origin="admin_suppliers")

def _current_period_label() -> str:
    window = get_current_open_window()
    return window["label"] if window else "Período atual"


def _get_upload_id_for_supplier(code: str) -> str | None:
    rows = get_admin_status_rows()
    row  = next((r for r in rows if r["code"].upper() == code.upper()), None)
    return row["upload_id"] if row else None


import re as _re
_EMAIL_RE = _re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _is_valid_email(email: str) -> bool:
    """Validação básica de formato de e-mail."""
    return bool(_EMAIL_RE.match(email.strip()))


def _email_exists(email: str, exclude_code: str | None = None) -> bool:
    """
    Verifica se o e-mail já está cadastrado.
    exclude_code: ignora o fornecedor com este código (para edição sem rejeitar o próprio e-mail).
    """
    email_lower = email.strip().lower()
    for s in get_all_suppliers():
        if exclude_code and s.code.upper() == exclude_code.upper():
            continue
        if s.email.strip().lower() == email_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# 1. Header integrado com botão Cadastrar
# ---------------------------------------------------------------------------

def _render_page_header() -> None:
    """Título/subtítulo à esquerda; '＋ Cadastrar Fornecedor' à direita."""
    period = _current_period_label()
    col_title, col_btn = st.columns([7, 2])

    with col_title:
        st.markdown(
            '<div class="kmt-section" style="margin-bottom:0;">'
            '<p class="kmt-section-title">Gestão de Distribuidores</p>'
            '<p class="kmt-section-subtitle">'
            'Cadastre, acompanhe e gerencie os distribuidores participantes '
            f'da coleta de forecast — <strong>{period}</strong>.'
            '</p></div>',
            unsafe_allow_html=True,
        )

    with col_btn:
        st.markdown('<div style="padding-top:14px;"></div>', unsafe_allow_html=True)
        current_mode = st.session_state.get("suppliers_form_mode")
        btn_label    = "✕  Fechar formulário" if current_mode == "add" else "＋  Cadastrar Distribuidor"
        if st.button(btn_label, key="btn_add_supplier", use_container_width=True):
            if current_mode == "add":
                st.session_state.suppliers_form_mode = None
            else:
                st.session_state.suppliers_form_mode    = "add"
                st.session_state.suppliers_edit_code    = None
                st.session_state.selected_supplier_code = None
                st.session_state.supplier_show_detail   = False
            safe_rerun()


# ---------------------------------------------------------------------------
# 2. Formulário inline (add / edit)
# ---------------------------------------------------------------------------

def _render_supplier_form() -> None:
    """
    Formulário de cadastro ou edição de fornecedor.

    Campos editáveis: Nome, E-mail, Status (Ativo/Inativo).
    Código: gerado automaticamente (add) ou somente leitura (edit).

    Regras de e-mail:
    - Obrigatório, formato básico válido, único, normalizado em minúsculas.
    - Usado como identificador de login futuro.

    Nota: fornecedor ativo participa da coleta; inativo não conta como pendente.
    Em produção, persistir em CONTROL.suppliers ou tabela equivalente no Snowflake.
    """
    # CSS para garantir contraste legível dentro do expander
    st.markdown(
        """
        <style>
        [data-testid="stExpander"] label,
        [data-testid="stExpander"] .stRadio > label,
        [data-testid="stExpander"] .stTextInput > label,
        [data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p {
            color: #1F2937 !important;
        }
        [data-testid="stExpander"] input[type="text"] {
            color: #1F2937 !important;
            background-color: #FFFFFF !important;
        }
        [data-testid="stExpander"] .stRadio span {
            color: #374151 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    mode      = st.session_state.get("suppliers_form_mode")
    edit_code = st.session_state.get("suppliers_edit_code")

    defaults: dict = {"name": "", "email": "", "status": "active"}
    if mode == "edit" and edit_code:
        s = get_supplier_by_code(edit_code)
        if s:
            defaults = {"name": s.name, "email": s.email, "status": s.status}

    auto_code  = get_next_supplier_code() if mode == "add" else edit_code
    form_title = "Cadastrar Distribuidor" if mode == "add" else f"Editar: {defaults['name']}"

    with st.expander(f"📝  {form_title}", expanded=True):

        # Código — somente leitura
        st.markdown(
            f'<p style="font-size:11px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.06em;color:#6B7280;margin:0 0 2px;">Código</p>'
            f'<p style="font-family:monospace;font-size:14px;font-weight:700;'
            f'color:#002B5C;margin:0 0 12px;">{auto_code}</p>',
            unsafe_allow_html=True,
        )

        with st.form("supplier_form", clear_on_submit=False):
            col_nome, col_email = st.columns([3, 3])
            with col_nome:
                nome = st.text_input(
                    "Nome do distribuidor",
                    value=defaults["name"],
                    placeholder="Ex: Distribuidora Centro Ltda",
                    key="sf_nome",
                )
            with col_email:
                email_input = st.text_input(
                    "E-mail do distribuidor",
                    value=defaults["email"],
                    placeholder="Ex: contato@distribuidora.com",
                    key="sf_email",
                    help="Será usado como identificador de login.",
                )

            status_val = st.radio(
                "Status",
                ["Ativo", "Inativo"],
                index=0 if defaults["status"] == "active" else 1,
                horizontal=True,
                key="sf_status",
            )

            col_save, col_cancel, _ = st.columns([2, 2, 6])
            with col_save:
                save_label = "Salvar distribuidor" if mode == "add" else "Salvar alterações"
                submitted  = st.form_submit_button(save_label, use_container_width=True)
            with col_cancel:
                cancelled = st.form_submit_button("Cancelar", use_container_width=True)

    if cancelled:
        st.session_state.suppliers_form_mode = None
        st.session_state.suppliers_edit_code = None
        safe_rerun()

    if submitted:
        nome_clean  = nome.strip()
        email_clean = email_input.strip().lower()
        error_msg   = None

        if not nome_clean:
            error_msg = "O nome do distribuidor é obrigatório."
        elif not email_clean:
            error_msg = "O e-mail do distribuidor é obrigatório."
        elif not _is_valid_email(email_clean):
            error_msg = f"O e-mail **{email_clean}** não tem um formato válido."
        elif _email_exists(email_clean, exclude_code=(edit_code if mode == "edit" else None)):
            error_msg = f"Já existe um distribuidor cadastrado com o e-mail **{email_clean}**."

        if error_msg:
            st.error(error_msg)
            return

        supplier_status = "active" if status_val == "Ativo" else "inactive"

        if mode == "add":
            result = create_supplier(nome_clean, email_clean, supplier_status)
            if result is None:
                st.error(
                    "Falha ao gravar distribuidor no Snowflake. "
                    "Verifique a conexão e tente novamente."
                )
                return
        else:
            supplier = get_supplier_by_code(edit_code)
            if supplier is None:
                st.error("Distribuidor não encontrado para edição.")
                return
            success = update_supplier(
                supplier.supplier_id, nome_clean, email_clean, supplier_status
            )
            if not success:
                st.error(
                    "Falha ao atualizar distribuidor no Snowflake. "
                    "Verifique a conexão e tente novamente."
                )
                return

        st.session_state.suppliers_form_mode  = None
        st.session_state.suppliers_edit_code  = None
        st.session_state.suppliers_just_saved = nome_clean
        safe_rerun()


# ---------------------------------------------------------------------------
# 3. Cards KPI
# ---------------------------------------------------------------------------

def _render_summary_cards(status_rows: list[dict]) -> None:
    """
    4 cards de resumo.
    Regra de pendência: fornecedores ativos sem forecast válido ativo no período.
    Inválidos contam como pendentes (conforme decisão funcional do painel admin).
    """
    from services.mock_data_service import get_current_open_window
    from services.upload_service import get_canceled_uploads_count

    summary   = get_summary()
    pendentes = sum(1 for r in status_rows if r["status"] == "pending")

    window = get_current_open_window()
    current_period = window["period"] if window else None
    cancelados = get_canceled_uploads_count(current_period) if current_period else 0

    render_cards_row([
        metric_card("Distribuidores Ativos",   str(summary["total_active"])),
        metric_card("Distribuidores Inativos", str(summary["total_inactive"])),
        metric_card("Pendentes no Período",  str(pendentes)),
        metric_card("Envios Cancelados",     str(cancelados)),
    ])


# ---------------------------------------------------------------------------
# 4. Filtros compactos (sem wrapper pesado)
# ---------------------------------------------------------------------------

def _render_filters(suppliers: list[SupplierRecord]) -> list[SupplierRecord]:
    """
    Filtros compactos: busca textual (nome/código) + 3 multiselects.
    Aplicados em ordem: busca → status → período → limite de 50 registros.
    Seleção vazia em multiselect = sem restrição para aquele filtro.
    """
    st.markdown(
        '<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:.06em;color:#9CA3AF;margin:0 0 6px;">Filtros</p>',
        unsafe_allow_html=True,
    )

    # ── Busca textual ─────────────────────────────────────────────────────────
    col_search, _ = st.columns([4, 4])
    with col_search:
        search_term = st.text_input(
            "Buscar",
            placeholder="Buscar por nome ou código do distribuidor",
            key="flt_search",
            label_visibility="collapsed",
        )

    # ── Multiselects ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    supplier_names = [s.name for s in suppliers]
    status_opts    = ["Ativo", "Inativo"]
    period_opts    = ["Válido", "Pendente", "Inválido", "Não esperado"]

    with col1:
        sel_suppliers = st.multiselect(
            "Todos os distribuidores",
            options=supplier_names,
            default=[],
            key="flt_supplier",
        )
    with col2:
        sel_status = st.multiselect(
            "Todos os status",
            options=status_opts,
            default=[],
            key="flt_status",
        )
    with col3:
        period_lbl = _current_period_label()
        sel_period = st.multiselect(
            f"Status {period_lbl}",
            options=period_opts,
            default=[],
            key="flt_period",
        )

    # ── Aplicar filtros ───────────────────────────────────────────────────────
    result = suppliers

    # 1. Busca textual por nome ou código (case-insensitive)
    if search_term.strip():
        term = search_term.strip().lower()
        result = [
            s for s in result
            if term in s.name.lower() or term in s.code.lower()
        ]

    # 2. Filtro de fornecedor (multiselect)
    if sel_suppliers:
        result = [s for s in result if s.name in sel_suppliers]

    # 3. Filtro de status
    if sel_status:
        status_map = {"Ativo": "active", "Inativo": "inactive"}
        allowed    = {status_map[x] for x in sel_status if x in status_map}
        result     = [s for s in result if s.status in allowed]

    # 4. Filtro de período
    if sel_period:
        period_map = {
            "Válido": "valid", "Pendente": "pending",
            "Inválido": "invalid", "Não esperado": "not_expected",
        }
        allowed = {period_map[x] for x in sel_period if x in period_map}
        result  = [s for s in result if s.period_status in allowed]

    # 5. Limite de exibição
    if len(result) > _DISPLAY_LIMIT:
        st.info(
            f"Exibindo os primeiros {_DISPLAY_LIMIT} de {len(result)} distribuidores. "
            f"Use os filtros ou a busca para refinar."
        )
        result = result[:_DISPLAY_LIMIT]

    return result


# ---------------------------------------------------------------------------
# 5. Tabela principal com coluna ⋮
# ---------------------------------------------------------------------------

def _render_suppliers_table(
    suppliers: list[SupplierRecord],
    selected_code: str | None,
    status_rows: list[dict],
) -> None:
    """
    Tabela simulada com st.columns por linha.
    Última coluna: st.popover("⋮") com menu de ações contextual.

    Ações condicionais por status:
    - Ativo:   Ver detalhe | Editar | ⚠ Inativar [| Ver erros se inválido]
    - Inativo: Ver detalhe | Editar | ✓ Ativar
    """
    # ── Cabeçalho ────────────────────────────────────────────────────────────
    hdr    = st.columns(_COLS)
    labels = [
        "Distribuidor", "E-mail", "Código", "Status",
        "Último Envio", f"Status {_current_period_label()}", "Ações",
    ]
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

    if not suppliers:
        st.markdown(
            '<p style="font-size:13px;color:#9CA3AF;padding:16px 0;">'
            'Nenhum distribuidor encontrado para os filtros selecionados.</p>',
            unsafe_allow_html=True,
        )
        return

    # ── Linhas da tabela ─────────────────────────────────────────────────────
    for s in suppliers:
        is_sel = selected_code == s.code

        # Encontrar status_row do fornecedor (para "Ver erros")
        sup_row           = next(
            (r for r in status_rows if r["code"].upper() == s.code.upper()), None
        )
        has_invalid       = sup_row is not None and sup_row["status"] == "invalid"
        invalid_upload_id = sup_row["upload_id"] if has_invalid else None

        row = st.columns(_COLS)

        with row[0]:
            weight = "700" if is_sel else "600"
            color  = "#002B5C" if is_sel else "#374151"
            st.markdown(
                f'<p style="font-size:13px;font-weight:{weight};color:{color};'
                f'margin:6px 0;">{s.name}</p>',
                unsafe_allow_html=True,
            )
        with row[1]:
            email_display = s.email if s.email else "—"
            st.markdown(
                f'<p style="font-size:11px;color:#6B7280;margin:6px 0;'
                f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"'
                f' title="{email_display}">{email_display}</p>',
                unsafe_allow_html=True,
            )
        with row[2]:
            st.markdown(
                f'<p style="font-family:monospace;font-size:12px;color:#6B7280;margin:6px 0;">'
                f'{s.code}</p>',
                unsafe_allow_html=True,
            )
        with row[3]:
            st.markdown(
                f'<div style="margin:4px 0;">{status_badge(s.status)}</div>',
                unsafe_allow_html=True,
            )
        with row[4]:
            st.markdown(
                f'<p style="font-size:12px;color:#374151;margin:6px 0;">'
                f'{s.last_upload}</p>',
                unsafe_allow_html=True,
            )
        with row[5]:
            st.markdown(
                f'<div style="margin:4px 0;">{status_badge(s.period_status)}</div>',
                unsafe_allow_html=True,
            )

        # ── Kebab menu via st.popover ─────────────────────────────────────────
        with row[6]:
            with st.popover("⋮", use_container_width=True):

                # Mini-cabeçalho de contexto
                st.markdown(
                    f'<p style="font-size:12px;font-weight:700;color:#002B5C;'
                    f'margin:0 0 8px;padding-bottom:8px;'
                    f'border-bottom:1px solid #F3F4F6;">'
                    f'{s.name}</p>',
                    unsafe_allow_html=True,
                )

                # Ver detalhe
                st.button(
                    "Ver detalhe",
                    key=f"pop_det_{s.code}",
                    use_container_width=True,
                    on_click=_cb_ver_detalhe,
                    args=(s.code,),
                )

                # Editar
                st.button(
                    "Editar",
                    key=f"pop_edit_{s.code}",
                    use_container_width=True,
                    on_click=_cb_editar,
                    args=(s.code,),
                )

                # Inativar / Ativar (condicional por status)
                if s.status == "active":
                    st.button(
                        "⚠  Inativar",
                        key=f"pop_inact_{s.code}",
                        use_container_width=True,
                        on_click=_cb_inativar,
                        args=(s.code, s.name),
                    )
                else:
                    st.button(
                        "✓  Ativar",
                        key=f"pop_act_{s.code}",
                        use_container_width=True,
                        on_click=_cb_ativar,
                        args=(s.code, s.name),
                    )

                # Ver erros (só quando inválido no período)
                if has_invalid and invalid_upload_id:
                    st.button(
                        "Ver erros",
                        key=f"pop_err_{s.code}",
                        use_container_width=True,
                        on_click=_cb_ver_erros,
                        args=(invalid_upload_id,),
                    )

        # Separador de linha
        st.markdown(
            '<div style="border-top:1px solid #F3F4F6;margin:0;"></div>',
            unsafe_allow_html=True,
        )



# ---------------------------------------------------------------------------
# Painel de detalhe do fornecedor
# ---------------------------------------------------------------------------

def _render_supplier_detail(code: str) -> None:
    """Detalhe inline: informações cadastrais + envios recentes reais da sessão."""
    from services.upload_service import get_supplier_uploads
    s = get_supplier_by_code(code)
    if s is None:
        return

    # BUG-05: usar uploads reais da sessão (s.recent_uploads sempre vazio para sessão)
    real_uploads = get_supplier_uploads(s.code, include_mock=False)

    uploads_html = ""
    for u in real_uploads:
        badge = status_badge(u.status)
        uploads_html += f"""
        <div style="display:flex;align-items:center;gap:12px;
                    padding:8px 0;border-bottom:1px solid #F3F4F6;font-size:13px;">
            <span style="font-weight:700;color:#002B5C;min-width:60px;">{u.period}</span>
            <span style="color:#6B7280;">{u.report_type}</span>
            <span style="color:#9CA3AF;font-size:11px;">Versão {u.version}</span>
            {badge}
        </div>"""

    if not uploads_html:
        uploads_html = (
            '<div style="font-size:12px;color:#9CA3AF;">Nenhum envio registrado</div>'
        )

    # Botão compacto de fechar o painel de detalhe
    col_close, _ = st.columns([2, 6])
    with col_close:
        if st.button("✕  Fechar detalhe", key="btn_close_detail", use_container_width=True):
            st.session_state.supplier_show_detail   = False
            st.session_state.selected_supplier_code = None
            safe_rerun()

    # BUG-06: HTML corrigido — sem blocos duplicados de "Último envio" e "Status no período"
    st.markdown(
        f"""
        <div class="kmt-card" style="margin:8px 0 0;">
            <div style="display:flex;align-items:center;justify-content:space-between;
                        margin-bottom:16px;padding-bottom:12px;
                        border-bottom:1px solid #F3F4F6;">
                <div>
                    <p class="kmt-card-label" style="margin-bottom:4px;">
                        Detalhe do Distribuidor
                    </p>
                    <p style="font-size:18px;font-weight:700;color:#002B5C;margin:0;">
                        {s.name}
                    </p>
                </div>
                <div style="text-align:right;">
                    <p style="font-family:monospace;font-size:13px;font-weight:700;
                              color:#6B7280;margin:0 0 6px;">{s.code}</p>
                    {status_badge(s.status)}
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
                <div>
                    <p class="kmt-card-label" style="margin-bottom:8px;">Informações</p>
                    <div style="font-size:13px;color:#374151;
                                display:flex;flex-direction:column;gap:8px;">
                        <div>
                            <span style="color:#9CA3AF;">E-mail:</span>
                            &nbsp;<span style="font-size:12px;font-family:monospace;">
                                {s.email if s.email else "—"}
                            </span>
                        </div>
                        <div>
                            <span style="color:#9CA3AF;">Último envio:</span>
                            &nbsp;<span style="font-weight:600;">{s.last_upload}</span>
                        </div>
                        <div>
                            <span style="color:#9CA3AF;">Status no período:</span>
                            &nbsp;{status_badge(s.period_status)}
                        </div>
                    </div>
                </div>
                <div>
                    <p class="kmt-card-label" style="margin-bottom:8px;">Envios Recentes</p>
                    {uploads_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def render() -> None:
    """
    Gestão de Fornecedores — estrutura CRUD administrativa.

    Hierarquia:
    1. Header com botão Cadastrar integrado
    2. Formulário (add/edit) — logo após header, quando ativo
    3. Mensagens de feedback
    4. Cards KPI
    5. Filtros multi-seleção
    6. Tabela com kebab menu (⋮) por linha — st.popover
    7. Painel de detalhe inline (quando Ver detalhe for clicado no menu)
    """
    try:
        _render_impl()
    except Exception as exc:
        from utils.logger import get_logger
        get_logger(__name__).exception("Erro ao renderizar Gestão de Distribuidores: %s", exc)
        st.error("Não foi possível carregar estas informações no momento. Tente novamente em alguns instantes.")


def _render_impl() -> None:
    """Implementação interna da tela de Gestão de Fornecedores."""
    all_suppliers = get_all_suppliers()
    status_rows   = get_admin_status_rows()

    # 1. Header + botão Cadastrar
    _render_page_header()

    # 2. Formulário inline (add/edit)
    if st.session_state.get("suppliers_form_mode"):
        st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
        _render_supplier_form()

    # 3. Mensagens de feedback (salvar / inativar / ativar)
    saved_msg  = st.session_state.get("suppliers_just_saved")
    status_msg = st.session_state.get("supplier_status_msg")
    if saved_msg:
        st.session_state.suppliers_just_saved = None
        st.success(f"Distribuidor **{saved_msg}** salvo com sucesso.")
    if status_msg:
        st.session_state.supplier_status_msg = None
        st.success(status_msg)

    # 4. Cards KPI (usa status_rows já calculado — sem chamada duplicada)
    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    _render_summary_cards(status_rows)

    # Estado vazio: nenhum fornecedor cadastrado (DEMO_MODE=False sem sessão)
    if not all_suppliers:
        st.markdown(
            """
            <div class="kmt-alert kmt-alert--info" style="margin-top:16px;">
                <div class="kmt-alert-icon">📋</div>
                <div>
                    <p class="kmt-alert-title">Nenhum distribuidor cadastrado.</p>
                    <p class="kmt-alert-body">
                        Clique em "＋ Cadastrar Distribuidor" para adicionar
                        o primeiro distribuidor participante da coleta.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # 5. Filtros multi-seleção
    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    filtered = _render_filters(all_suppliers)

    # Fechar detalhe automaticamente se o fornecedor selecionado não está mais visível
    # (ex: admin filtrou por Status=Inativo e o fornecedor ativo que estava aberto sumiu)
    if (
        st.session_state.get("supplier_show_detail")
        and st.session_state.get("selected_supplier_code")
    ):
        visible_codes = {s.code.upper() for s in filtered}
        if st.session_state.selected_supplier_code.upper() not in visible_codes:
            st.session_state.supplier_show_detail   = False
            st.session_state.selected_supplier_code = None

    # 6. Tabela com kebab menu (⋮ / st.popover) por linha
    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)
    selected_code = st.session_state.get("selected_supplier_code")
    _render_suppliers_table(filtered, selected_code, status_rows)

    # 7. Painel de detalhe (visível quando "Ver detalhe" foi clicado no kebab menu)
    if (
        st.session_state.get("supplier_show_detail")
        and st.session_state.get("selected_supplier_code")
        and not st.session_state.get("suppliers_form_mode")
    ):
        _render_supplier_detail(st.session_state.selected_supplier_code)
