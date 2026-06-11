"""
komatsu_ds.layout
=================
Estrutura, navegação e disposição de páginas para dashboards Komatsu no Streamlit.

Fonte oficial: docs/ui_skills/layout_SKILL.md

Funções disponíveis:
    setup_page          — configura a página (DEVE ser a primeira chamada Streamlit)
    page_header         — cabeçalho H1 + subtítulo + hint de fonte
    section_header      — separador visual interno de seção
    kpi_row             — linha de KPI cards em colunas automáticas
    kpi_row_horizontal  — KPI cards com ícone grande à esquerda
    columns_2           — grid de 2 colunas com proporção configurável
    columns_3           — grid de 3 colunas com proporção configurável
    columns_4           — grid de 4 colunas iguais
    columns_n           — grid de N colunas iguais
    divider             — linha horizontal sutil
    filter_bar          — context manager: filtros horizontais em card branco
    empty_state         — estado vazio centralizado com ícone e mensagem

NÃO implementado nesta etapa (dependem da sidebar role-aware do portal):
    sidebar()           — context manager genérico (substituiria navigation.py)
    sidebar_nav()       — navegação sem filtros

Imports:
    import streamlit as st
    from contextlib import contextmanager
    from komatsu_ds import colors as C
"""

import streamlit as st
from contextlib import contextmanager

from komatsu_ds import colors as C


# =============================================================================
# 1. Setup da Página
# =============================================================================

def setup_page(
    title: str,
    icon: str = "📊",
    layout_mode: str = "wide",
    sidebar_state: str = "expanded",
) -> None:
    """
    Configura a página Streamlit com identidade visual Komatsu.

    ATENÇÃO: deve ser a PRIMEIRA chamada Streamlit de cada arquivo de página.
    Chama st.set_page_config() internamente — se chamado mais de uma vez por
    sessão, o Streamlit lança StreamlitAPIException.

    Parâmetros:
        title         — título da aba do navegador (ex: "Painel | Komatsu")
        icon          — emoji ou URL de imagem para a aba (default: "📊")
        layout_mode   — "wide" (default) | "centered"
        sidebar_state — "expanded" (default) | "collapsed"

    Uso:
        layout.setup_page("Portal de Coleta | Komatsu", icon="📦")
    """
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout_mode,
        initial_sidebar_state=sidebar_state,
    )
    # Injeção de CSS do design system será ativada quando ds.css estiver
    # finalizado. Por enquanto, setup_page apenas configura a página.
    # _inject_ds_css()


# =============================================================================
# 2. Cabeçalho de Página
# =============================================================================

def page_header(
    title: str,
    subtitle: str | None = None,
    source_hint: str | None = None,
) -> None:
    """
    Renderiza o cabeçalho de página: H1 + subtítulo em cinza + hint de fonte.
    Deve vir logo após o bloco de carregamento de dados.

    Parâmetros:
        title       — texto principal (H1)
        subtitle    — subtítulo opcional exibido em cinza abaixo do título
        source_hint — nome(s) de tabela/fonte exibido(s) em bloco <code>

    Uso:
        layout.page_header(
            "Painel de Coleta de Forecast",
            subtitle="Visao consolidada por distribuidor",
            source_hint="uploads · suppliers",
        )
    """
    subtitle_html = (
        f'<p style="'
        f'color:{C.NEUTRO_3};font-size:14px;'
        f'font-family:Inter,sans-serif;margin:4px 0 0;line-height:1.4;">'
        f'{subtitle}</p>'
        if subtitle else ""
    )
    source_html = (
        f'<p style="margin:8px 0 0;">'
        f'<code style="'
        f'font-size:12px;color:{C.NEUTRAL_7};'
        f'background:{C.NEUTRAL_2};'
        f'padding:2px 8px;border-radius:4px;">'
        f'{source_hint}</code></p>'
        if source_hint else ""
    )
    st.markdown(
        f"""
        <div style="margin-bottom:20px;padding-bottom:4px;">
            <h1 style="
                color:{C.GLORIA_BLUE_P1};
                font-family:Inter,sans-serif;
                font-size:24px;font-weight:600;
                margin:0;line-height:1.3;
            ">{title}</h1>
            {subtitle_html}
            {source_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 3. Cabeçalho de Seção
# =============================================================================

def section_header(title: str, icon: str | None = None) -> None:
    """
    Separador visual interno à página.
    Fonte Inter 600, cor #0C065C (GLORIA_BLUE_P1), borda inferior azul.

    Parâmetros:
        title — texto da seção
        icon  — emoji opcional exibido antes do texto

    Uso:
        layout.section_header("KPIs do Período", "📈")
        layout.section_header("Detalhamento de Erros")
    """
    prefix = f"{icon}&nbsp;" if icon else ""
    st.markdown(
        f"""
        <div style="
            border-bottom:2px solid {C.GLORIA_BLUE_P1};
            padding-bottom:6px;
            margin:24px 0 16px;
        ">
            <span style="
                font-family:Inter,sans-serif;
                font-size:15px;font-weight:600;
                color:{C.GLORIA_BLUE_P1};
            ">{prefix}{title}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 4. KPI Cards — helpers internos
# =============================================================================

def _kpi_card_html(card: dict, compact: bool = False) -> str:
    """
    Retorna o HTML de um único KPI card (uso interno por kpi_row).

    Chaves aceitas no dict:
        label   — rótulo acima do valor (obrigatório)
        value   — valor principal em destaque (obrigatório)
        delta   — variação: verde se não começa com "-", vermelho se "-"
        icon    — emoji exibido acima do label
        neutral — True → delta exibido em cinza, sem direção
    """
    label   = card.get("label", "")
    value   = card.get("value", "—")
    delta   = card.get("delta")
    icon    = card.get("icon")
    neutral = card.get("neutral", False)

    value_size = "26px" if compact else "32px"
    label_size = "12px" if compact else "13px"
    padding    = "14px 12px" if compact else "20px 16px"

    # Delta: cor e seta
    if delta:
        if neutral:
            delta_color = C.NEUTRO_4
            delta_arrow = ""
        elif str(delta).startswith("-"):
            delta_color = C.RED
            delta_arrow = "▼ "
        else:
            delta_color = C.GREEN
            delta_arrow = "▲ "
        delta_html = (
            f'<div style="'
            f'font-size:13px;font-weight:700;'
            f'color:{delta_color};margin-top:4px;'
            f'font-family:\'Segoe UI\',Inter,sans-serif;">'
            f'{delta_arrow}{delta}</div>'
        )
    else:
        delta_html = ""

    icon_html = (
        f'<div style="font-size:20px;margin-bottom:4px;">{icon}</div>'
        if icon else ""
    )

    return (
        f'<div style="'
        f'background:{C.NEUTRAL_1};'
        f'border-radius:15px;'
        f'box-shadow:0 1px 6px rgba(0,0,0,0.08);'
        f'padding:{padding};'
        f'text-align:center;">'
        f'{icon_html}'
        f'<div style="font-size:{label_size};color:{C.NEUTRAL_8};'
        f'font-family:\'Segoe UI\',Inter,sans-serif;">{label}</div>'
        f'<div style="font-size:{value_size};font-weight:700;color:#000000;'
        f'font-family:\'Segoe UI\',Inter,sans-serif;margin-top:6px;">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


# =============================================================================
# 5. kpi_row — linha de KPI cards
# =============================================================================

def kpi_row(cards: list[dict], compact: bool = False) -> None:
    """
    Monta automaticamente N colunas e renderiza um KPI card por item.

    Chaves de cada dict:
        label   — texto do rótulo (obrigatório)
        value   — valor principal (obrigatório)
        delta   — variação (▲ verde se não "-", ▼ vermelho se começa com "-")
        icon    — emoji acima do label
        neutral — True → delta exibido em cinza, sem seta

    Parâmetros:
        cards   — lista de dicts com os dados de cada card
        compact — True para versão com fonte reduzida (6+ cards)

    Uso:
        layout.kpi_row([
            {"label": "Taxa de Sucesso", "value": "98.2%", "delta": "+1.3%", "icon": "✅"},
            {"label": "Total de Envios", "value": "1.234", "neutral": True,  "icon": "📤"},
            {"label": "Erros",           "value": "22",    "delta": "-5",    "icon": "❌"},
        ])
    """
    if not cards:
        return
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(_kpi_card_html(card, compact=compact), unsafe_allow_html=True)


# =============================================================================
# 6. kpi_row_horizontal — cards com ícone à esquerda
# =============================================================================

def kpi_row_horizontal(cards: list[dict]) -> None:
    """
    Cards mais largos com ícone grande à esquerda — ideal para painéis de alertas.

    Chaves aceitas: icon, label, value, delta, neutral.

    Uso:
        layout.kpi_row_horizontal([
            {"icon": "🔴", "label": "Runs com Falha",  "value": "7",   "delta": "3.2% do total"},
            {"icon": "⚠️", "label": "DAGs Afetadas",   "value": "4",   "neutral": True},
        ])
    """
    if not cards:
        return
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        icon    = card.get("icon", "")
        label   = card.get("label", "")
        value   = card.get("value", "—")
        delta   = card.get("delta")
        neutral = card.get("neutral", False)

        if delta:
            if neutral:
                delta_color = C.NEUTRO_4
                delta_arrow = ""
            elif str(delta).startswith("-"):
                delta_color = C.RED
                delta_arrow = "▼ "
            else:
                delta_color = C.GREEN
                delta_arrow = "▲ "
            delta_html = (
                f'<div style="font-size:12px;font-weight:600;'
                f'color:{delta_color};margin-top:2px;">'
                f'{delta_arrow}{delta}</div>'
            )
        else:
            delta_html = ""

        with col:
            st.markdown(
                f"""
                <div style="
                    background:{C.NEUTRAL_1};
                    border-radius:15px;
                    box-shadow:0 1px 6px rgba(0,0,0,0.08);
                    padding:16px 20px;
                    display:flex;
                    align-items:center;
                    gap:16px;
                ">
                    <div style="font-size:32px;line-height:1;flex-shrink:0;">{icon}</div>
                    <div>
                        <div style="font-size:12px;color:{C.NEUTRAL_8};
                                    font-family:'Segoe UI',Inter,sans-serif;">{label}</div>
                        <div style="font-size:26px;font-weight:700;color:#000000;
                                    font-family:'Segoe UI',Inter,sans-serif;">{value}</div>
                        {delta_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =============================================================================
# 7. Grids de Colunas
# =============================================================================

def columns_2(ratio: tuple = (1, 1), gap: str = "medium"):
    """
    Retorna 2 colunas com proporção configurável.

    Parâmetros:
        ratio — tupla de 2 pesos, ex: (2, 1) → 66% / 33%
        gap   — "small" | "medium" (default) | "large"

    Uso:
        col_l, col_r = layout.columns_2()
        col_l, col_r = layout.columns_2(ratio=(2, 1))
    """
    return st.columns(list(ratio), gap=gap)


def columns_3(ratio: tuple = (1, 1, 1), gap: str = "medium"):
    """
    Retorna 3 colunas com proporção configurável.

    Uso:
        c1, c2, c3 = layout.columns_3()
        c1, c2, c3 = layout.columns_3(ratio=(2, 1, 1))
    """
    return st.columns(list(ratio), gap=gap)


def columns_4(gap: str = "medium"):
    """
    Retorna 4 colunas iguais.

    Uso:
        c1, c2, c3, c4 = layout.columns_4()
    """
    return st.columns(4, gap=gap)


def columns_n(n: int, gap: str = "medium"):
    """
    Retorna N colunas iguais (qualquer número).

    Parâmetros:
        n   — número de colunas
        gap — "small" | "medium" (default) | "large"

    Uso:
        cols = layout.columns_n(6)
        cols = layout.columns_n(4, gap="large")
    """
    return st.columns(n, gap=gap)


# =============================================================================
# 8. Divisor Horizontal
# =============================================================================

def divider() -> None:
    """
    Linha horizontal sutil (NEUTRAL_3 = #E4E6E6).
    Use para separar blocos dentro de uma página.

    Uso:
        layout.divider()
    """
    st.markdown(
        f'<hr style="'
        f'border:none;'
        f'border-top:1px solid {C.NEUTRAL_3};'
        f'margin:16px 0;'
        f'">',
        unsafe_allow_html=True,
    )


# =============================================================================
# 9. Barra de Filtros Inline
# =============================================================================

@contextmanager
def filter_bar():
    """
    Context manager que envolve filtros horizontais em um card branco.

    Uso:
        with layout.filter_bar():
            fc1, fc2, fc3 = st.columns([1, 1, 2])
            with fc1:
                periodo = st.selectbox("Período", ["7d", "14d", "30d"])
            with fc2:
                owner = st.selectbox("Owner", owners)
    """
    st.markdown(
        f"""
        <div style="
            background:{C.NEUTRAL_1};
            border-radius:12px;
            padding:16px 20px;
            box-shadow:0 1px 3px rgba(0,0,0,0.06);
            margin-bottom:16px;
        ">
        """,
        unsafe_allow_html=True,
    )
    yield
    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# 10. Estado Vazio
# =============================================================================

def empty_state(
    message: str = "Nenhum dado encontrado para os filtros selecionados.",
    icon: str = "🔍",
) -> None:
    """
    Exibe estado vazio centralizado com ícone e mensagem.

    Parâmetros:
        message — texto exibido abaixo do ícone
        icon    — emoji exibido acima da mensagem

    Uso:
        layout.empty_state("Nenhuma falha registrada no período! 🎉", icon="✅")
        layout.empty_state()   # padrão: 🔍 + mensagem genérica
    """
    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding:48px 24px;
            color:{C.NEUTRAL_7};
        ">
            <div style="font-size:36px;margin-bottom:12px;">{icon}</div>
            <div style="
                font-size:14px;
                font-family:Inter,sans-serif;
                line-height:1.6;
            ">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
