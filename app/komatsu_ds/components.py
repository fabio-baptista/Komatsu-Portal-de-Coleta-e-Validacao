"""
komatsu_ds.components
=====================
Catálogo de componentes visuais do Komatsu Design System para Streamlit.

Fonte oficial: docs/ui_skills/components_SKILL.md

Componentes disponíveis nesta etapa:
    badge               — badge de estado colorido (retorna HTML string)
    info_card           — card de metadados key-value
    kpi_card            — KPI card padrão vertical
    kpi_card_compact    — KPI card compacto (6+ cards)
    kpi_card_horizontal — KPI card com ícone grande à esquerda
    render_table        — tabela estilizada via st.dataframe
    section_header      — cabeçalho de seção (disponível aqui por conveniência)
    render_chart        — exibe go.Figure em card branco (requer plotly)

Funções de gráfico NÃO implementadas nesta etapa (plotly ausente em requirements.txt
e portal atual não usa gráficos):
    bar_chart, stacked_bar_chart, line_chart, area_chart, donut_chart,
    scatter_chart, histogram, heatmap, funnel_chart, gauge_chart

Imports:
    import streamlit as st
    from komatsu_ds import colors as C
"""

import streamlit as st

from komatsu_ds import colors as C


# =============================================================================
# Mapeamento de variantes de badge
# =============================================================================

_BADGE_VARIANTS: dict[str, dict[str, str]] = {
    "success": {
        "bg":    C.GREEN_LIGHT,   # #AAE2C7
        "color": C.GREEN_DARK,    # #11492E
    },
    "warning": {
        "bg":    C.YELLOW_M3,     # #FFE9AC
        "color": C.YELLOW_P3,     # #665013
    },
    "error": {
        "bg":    C.RED_LIGHT,     # #FF9999
        "color": C.RED_DARK,      # #660000
    },
    "failed": {
        "bg":    C.RED_LIGHT,     # #FF9999
        "color": C.RED_DARK,      # #660000
    },
    "running": {
        "bg":    C.SEC_BLUE_LIGHT, # #99DCF3
        "color": C.SEC_BLUE_DARK,  # #004359
    },
    "info": {
        "bg":    C.GLORIA_BLUE_M4, # #99CCFF
        "color": C.GLORIA_BLUE_P1, # #0C065C
    },
    "neutral": {
        "bg":    C.NEUTRAL_2,      # #F6F6F6
        "color": C.NEUTRAL_8,      # #4C5459
    },
}


# =============================================================================
# 1. badge — badge de estado colorido
# =============================================================================

def badge(text: str, variant: str = "neutral") -> str:
    """
    Retorna HTML de um badge colorido. NÃO renderiza — retorne com st.markdown.

    Variantes disponíveis:
        "success"  — verde  (#AAE2C7 / #11492E) — Active, Done, Success
        "warning"  — amarelo (#FFE9AC / #665013) — Paused, Queued, Pending
        "error"    — vermelho (#FF9999 / #660000) — Failed, Error
        "failed"   — idêntico a "error"
        "running"  — azul claro (#99DCF3 / #004359) — Running, In Progress
        "info"     — azul (#99CCFF / #0C065C) — Informativo neutro
        "neutral"  — cinza (#F6F6F6 / #4C5459) — Default sem estado

    Parâmetros:
        text    — texto exibido no badge
        variant — uma das variantes acima (default: "neutral")

    Uso:
        html = comp.badge("Active",   "success")
        html = comp.badge("Paused",   "warning")
        html = comp.badge("Failed",   "error")
        html = comp.badge("Running",  "running")
        st.markdown(comp.badge("Info", "info"), unsafe_allow_html=True)
    """
    cfg = _BADGE_VARIANTS.get(variant, _BADGE_VARIANTS["neutral"])
    return (
        f'<span style="'
        f'display:inline-block;'
        f'padding:3px 10px;'
        f'border-radius:9999px;'
        f'font-size:11px;'
        f'font-weight:600;'
        f'font-family:Inter,\'Segoe UI\',sans-serif;'
        f'background:{cfg["bg"]};'
        f'color:{cfg["color"]};'
        f'white-space:nowrap;'
        f'line-height:1.6;'
        f'">{text}</span>'
    )


# =============================================================================
# 2. info_card — card de metadados key-value
# =============================================================================

def info_card(title: str, items: dict) -> None:
    """
    Renderiza um card branco com título e pares chave-valor.
    Ideal para detalhes de uma entidade (upload, fornecedor, run).

    Aceita HTML como valor — útil para embutir badges.

    Parâmetros:
        title — título do card
        items — dict {chave: valor}, onde valor pode ser string HTML

    Uso:
        comp.info_card(
            "Detalhes do Envio",
            {
                "Status":   comp.badge("Válido", "success"),
                "Arquivo":  "forecast_jan.xlsx",
                "Período":  "2025-01",
                "Versão":   "v2",
            }
        )
    """
    rows_html = "".join(
        f"""
        <tr>
            <td style="
                padding:8px 12px;
                font-size:12px;
                font-weight:600;
                color:{C.NEUTRAL_7};
                font-family:Inter,sans-serif;
                white-space:nowrap;
                border-bottom:1px solid {C.NEUTRAL_3};
                vertical-align:middle;
            ">{key}</td>
            <td style="
                padding:8px 12px;
                font-size:13px;
                color:{C.NEUTRAL_8};
                font-family:Inter,sans-serif;
                border-bottom:1px solid {C.NEUTRAL_3};
                vertical-align:middle;
            ">{value}</td>
        </tr>
        """
        for key, value in items.items()
    )

    st.markdown(
        f"""
        <div style="
            background:{C.NEUTRAL_1};
            border-radius:15px;
            box-shadow:0 1px 6px rgba(0,0,0,0.08);
            padding:0;
            overflow:hidden;
        ">
            <div style="
                padding:12px 16px;
                border-bottom:2px solid {C.GLORIA_BLUE_P1};
            ">
                <span style="
                    font-size:14px;
                    font-weight:600;
                    color:{C.GLORIA_BLUE_P1};
                    font-family:Inter,sans-serif;
                ">{title}</span>
            </div>
            <table style="width:100%;border-collapse:collapse;">
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Helpers internos de KPI card
# =============================================================================

def _delta_html(delta: str | None, neutral: bool, font_size: str = "13px") -> str:
    """Gera o HTML do delta com cor e seta adequados."""
    if not delta:
        return ""
    if neutral:
        color = C.NEUTRO_4
        arrow = ""
    elif str(delta).startswith("-"):
        color = C.RED
        arrow = "▼ "
    else:
        color = C.GREEN
        arrow = "▲ "
    return (
        f'<div style="'
        f'font-size:{font_size};font-weight:700;'
        f'color:{color};margin-top:4px;'
        f'font-family:\'Segoe UI\',Inter,sans-serif;">'
        f'{arrow}{delta}</div>'
    )


# =============================================================================
# 3. kpi_card — KPI card padrão vertical
# =============================================================================

def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    icon: str | None = None,
    neutral: bool = False,
) -> None:
    """
    Renderiza um KPI card vertical padrão diretamente.

    Parâmetros:
        label   — rótulo acima do valor
        value   — valor principal em destaque
        delta   — variação (▲ verde | ▼ vermelho | cinza se neutral=True)
        icon    — emoji exibido acima do label
        neutral — True → delta exibido em cinza sem seta

    Uso:
        comp.kpi_card("Taxa de Sucesso", "98.2%", delta="+1.3%", icon="✅")

    Prefira layout.kpi_row([...]) para múltiplos cards — cria colunas automaticamente.
    """
    icon_html = (
        f'<div style="font-size:20px;margin-bottom:4px;">{icon}</div>'
        if icon else ""
    )
    st.markdown(
        f"""
        <div style="
            background:{C.NEUTRAL_1};
            border-radius:15px;
            box-shadow:0 1px 6px rgba(0,0,0,0.08);
            padding:20px 16px;
            text-align:center;
        ">
            {icon_html}
            <div style="
                font-size:13px;color:{C.NEUTRAL_8};
                font-family:'Segoe UI',Inter,sans-serif;
            ">{label}</div>
            <div style="
                font-size:32px;font-weight:700;color:#000000;
                font-family:'Segoe UI',Inter,sans-serif;margin-top:6px;
            ">{value}</div>
            {_delta_html(delta, neutral)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 4. kpi_card_compact — KPI card compacto
# =============================================================================

def kpi_card_compact(
    label: str,
    value: str,
    delta: str | None = None,
    neutral: bool = False,
) -> None:
    """
    Versão compacta do KPI card — fonte menor.
    Use quando há 6 ou mais cards na linha.

    Parâmetros:
        label   — rótulo acima do valor
        value   — valor principal
        delta   — variação opcional
        neutral — True → delta em cinza sem seta
    """
    st.markdown(
        f"""
        <div style="
            background:{C.NEUTRAL_1};
            border-radius:15px;
            box-shadow:0 1px 6px rgba(0,0,0,0.08);
            padding:14px 12px;
            text-align:center;
        ">
            <div style="
                font-size:12px;color:{C.NEUTRAL_8};
                font-family:'Segoe UI',Inter,sans-serif;
            ">{label}</div>
            <div style="
                font-size:26px;font-weight:700;color:#000000;
                font-family:'Segoe UI',Inter,sans-serif;margin-top:4px;
            ">{value}</div>
            {_delta_html(delta, neutral, font_size="12px")}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 5. kpi_card_horizontal — KPI card com ícone à esquerda
# =============================================================================

def kpi_card_horizontal(
    icon: str,
    label: str,
    value: str,
    delta: str | None = None,
    neutral: bool = False,
) -> None:
    """
    KPI card com ícone grande à esquerda — ideal para painéis de alerta.

    Parâmetros:
        icon    — emoji grande exibido à esquerda
        label   — rótulo acima do valor
        value   — valor principal
        delta   — variação opcional
        neutral — True → delta em cinza sem seta

    Uso:
        comp.kpi_card_horizontal("🔴", "Runs com Falha", "7", delta="3.2% do total")
    """
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
                <div style="
                    font-size:12px;color:{C.NEUTRAL_8};
                    font-family:'Segoe UI',Inter,sans-serif;
                ">{label}</div>
                <div style="
                    font-size:26px;font-weight:700;color:#000000;
                    font-family:'Segoe UI',Inter,sans-serif;
                ">{value}</div>
                {_delta_html(delta, neutral, font_size="12px")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 6. render_table — tabela estilizada via st.dataframe
# =============================================================================

def render_table(df, height: int = 400, hide_index: bool = True) -> None:
    """
    Exibe um DataFrame como tabela estilizada via st.dataframe.

    Não altera os dados, não acessa services nem session_state.

    Parâmetros:
        df         — pd.DataFrame a exibir
        height     — altura em pixels (default: 400)
        hide_index — ocultar índice (default: True)

    Uso:
        comp.render_table(df)
        comp.render_table(df[["Coluna A", "Coluna B"]], height=320)
    """
    st.dataframe(df, height=height, hide_index=hide_index, use_container_width=True)


# =============================================================================
# 7. section_header — cabeçalho de seção (conveniência)
# =============================================================================

def section_header(title: str, icon: str | None = None) -> None:
    """
    Separador visual interno à página.
    Idêntico a layout.section_header() — disponível aqui por conveniência.

    Parâmetros:
        title — texto da seção
        icon  — emoji opcional exibido antes do texto

    Uso:
        comp.section_header("KPIs de Tasks", "🔧")
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
# 8. render_chart — exibe go.Figure em card branco (requer plotly)
# =============================================================================

def render_chart(fig, title: str | None = None, subtitle: str | None = None, height: int | None = None) -> None:
    """
    Envolve qualquer go.Figure no card branco do design system e exibe com
    st.plotly_chart().

    REQUER plotly instalado. Se plotly não estiver disponível, exibe aviso.

    Parâmetros:
        fig      — go.Figure retornado por qualquer função de gráfico do DS
        title    — título exibido acima do gráfico
        subtitle — subtítulo opcional em cinza
        height   — sobrescreve a altura da figura se informado

    Uso:
        fig = comp.bar_chart(df, x="mes", y="valor")   # (etapa futura)
        comp.render_chart(fig, title="Vendas por Mês", subtitle="Últimos 12 meses")

    Nota: plotly não está em requirements.txt nesta etapa.
    Funções de gráfico (bar_chart, line_chart, etc.) serão adicionadas quando
    plotly for incluído no projeto.
    """
    try:
        import plotly.graph_objects as go  # noqa: F401
    except ImportError:
        st.warning(
            "render_chart requer plotly. "
            "Adicione `plotly` ao requirements.txt para usar gráficos do DS."
        )
        return

    if height is not None:
        fig.update_layout(height=height)

    title_html = (
        f'<div style="'
        f'font-size:15px;font-weight:600;color:{C.GLORIA_BLUE_P1};'
        f'font-family:Inter,sans-serif;margin-bottom:2px;">'
        f'{title}</div>'
        if title else ""
    )
    subtitle_html = (
        f'<div style="font-size:12px;color:{C.NEUTRO_3};'
        f'font-family:Inter,sans-serif;margin-bottom:10px;">'
        f'{subtitle}</div>'
        if subtitle else ""
    )

    st.markdown(
        f"""
        <div style="
            background:{C.NEUTRAL_1};
            border-radius:15px;
            box-shadow:0 1px 6px rgba(0,0,0,0.08);
            padding:20px 16px 12px;
        ">
            {title_html}
            {subtitle_html}
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
