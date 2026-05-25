"""
komatsu_ds.colors
=================
Tokens de cor, paletas e helpers do Komatsu Design System.

Fonte oficial: docs/ui_skills/colors_SKILL.md
Não importa nada do app funcional — apenas constantes Python puras.

Uso:
    from komatsu_ds import colors as C

    fig = px.bar(..., color_discrete_sequence=[C.GLORIA_BLUE, C.SEC_BLUE])
    cor = C.state_color("failed")          # → "#FF0000"
    cores = C.palette(3)                   # → ["#140A9A", "#00A7E1", "#FFC82F"]
"""

# =============================================================================
# Gloria Blue — paleta principal
# =============================================================================

GLORIA_BLUE_P3 = "#04121F"   # Near-black, contraste extremo
GLORIA_BLUE_P2 = "#08043E"   # Fundo escuro profundo (uso raro)
GLORIA_BLUE_P1 = "#0C065C"   # Títulos de seção, bordas accent
GLORIA_BLUE    = "#140A9A"   # PRIMARY — sidebar, botões ativos, série 1  ⭐
GLORIA_BLUE_M1 = "#253FC8"   # Hover de botão primário
GLORIA_BLUE_M2 = "#3366CC"   # Links secundários
GLORIA_BLUE_M3 = "#6699FF"   # Accent azul claro
GLORIA_BLUE_M4 = "#99CCFF"   # Labels sidebar inativo, texto muted em fundo escuro
GLORIA_BLUE_M5 = "#E2F2FF"   # Background de página, seções claras

# =============================================================================
# Natural Yellow — paleta principal
# =============================================================================

YELLOW_P3 = "#665013"   # Texto amarelo escuro / contraste
YELLOW_P2 = "#99781C"   # Ícone ou borda amarela escura
YELLOW_P1 = "#CCA026"   # Accent escuro
YELLOW    = "#FFC82F"   # ACCENT — série 3, highlights, warnings  ⭐
YELLOW_M1 = "#FFD359"   # Highlight amarelo claro
YELLOW_M2 = "#FFDE82"   # Tint amarelo sutil
YELLOW_M3 = "#FFE9AC"   # Background de badge warning
YELLOW_M4 = "#FFF4D5"   # Near-white amarelo

# =============================================================================
# Web Orange
# =============================================================================

WEB_ORANGE = "#F7A600"   # Accent laranja (usar com parcimônia)

# =============================================================================
# Secondary Blue
# =============================================================================

SEC_BLUE_DARK  = "#004359"   # Teal escuro, fundos profundos
SEC_BLUE       = "#00A7E1"   # Série 2, accent complementar  ⭐
SEC_BLUE_LIGHT = "#99DCF3"   # Tint azul claro

# =============================================================================
# Secondary Pink & Purple
# =============================================================================

SEC_PINK_DARK   = "#A5005A"
SEC_PINK        = "#E7218D"   # Série 4, decorativo
SEC_PINK_LIGHT  = "#F6ADD7"

SEC_PURPLE_DARK  = "#3C1A56"
SEC_PURPLE       = "#7030A0"   # Série 5, decorativo
SEC_PURPLE_LIGHT = "#A568D2"

# =============================================================================
# Feedback — Positive (Green)
# =============================================================================

GREEN_DARK  = "#11492E"   # Texto verde escuro
GREEN       = "#2BB673"   # Delta positivo ▲, estados de sucesso  ⭐
GREEN_LIGHT = "#AAE2C7"   # Background de badge success

# =============================================================================
# Feedback — Negative (Red)
# =============================================================================

RED_DARK  = "#660000"   # Texto vermelho escuro
RED       = "#FF0000"   # Delta negativo ▼, estados de erro/falha  ⭐
RED_LIGHT = "#FF9999"   # Background de badge failed

# =============================================================================
# Escala de Cinzas / Neutros
# =============================================================================

NEUTRAL_9 = "#2A3238"   # Labels de gráfico, texto pequeno, ícones
NEUTRAL_8 = "#4C5459"   # Texto body/parágrafo
NEUTRAL_7 = "#6E757A"   # Subtexto, captions
NEUTRAL_6 = "#8F969A"   # Placeholder
NEUTRAL_5 = "#A5ABAF"   # Elementos desabilitados
NEUTRAL_4 = "#C7CACD"   # Bordas, divisores
NEUTRAL_3 = "#E4E6E6"   # Bordas claras, linhas
NEUTRAL_2 = "#F6F6F6"   # Backgrounds sutis
NEUTRAL_1 = "#FFFFFF"   # Cards, branco puro
NEUTRO_3  = "#666666"   # Texto de descrição/subtítulo
NEUTRO_4  = "#9E9E9E"   # Texto cinza claro

# =============================================================================
# Sequência de séries para gráficos
# Sempre use esta ordem — nunca cores ad-hoc para séries
# =============================================================================

CHART_COLORS: list[str] = [
    "#140A9A",   # 1 — Gloria Blue Original  (série principal)
    "#00A7E1",   # 2 — Secondary Blue
    "#FFC82F",   # 3 — Natural Yellow
    "#E7218D",   # 4 — Secondary Pink
    "#7030A0",   # 5 — Secondary Purple
    "#0C065C",   # 6 — Gloria Blue +1 (mais escuro)
    "#99CCFF",   # 7 — Gloria Blue -4 (mais claro)
    "#F7A600",   # 8 — Web Orange
]

# =============================================================================
# Escalas sequenciais para Plotly
# =============================================================================

# Branco → Gloria Blue (heatmaps, choropleth)
HEATMAP_SCALE: list[list] = [
    [0, GLORIA_BLUE_M5],   # "#E2F2FF"
    [1, GLORIA_BLUE],      # "#140A9A"
]

# Verde → Amarelo → Vermelho (performance, divergente)
DIVERGING_GR: list[str] = [
    GREEN,        # "#2BB673"
    GREEN_LIGHT,  # "#AAE2C7"
    NEUTRAL_1,    # "#FFFFFF"
    RED_LIGHT,    # "#FF9999"
    RED,          # "#FF0000"
]

# =============================================================================
# Mapa de estados de pipeline
# Use em gráficos: color_map=C.STATE_COLORS
# =============================================================================

STATE_COLORS: dict[str, str] = {
    "success":         GREEN,          # "#2BB673"
    "succeeded":       GREEN,
    "done":            GREEN,
    "failed":          RED,            # "#FF0000"
    "error":           RED,
    "running":         SEC_BLUE,       # "#00A7E1"
    "in_progress":     SEC_BLUE,
    "queued":          YELLOW,         # "#FFC82F"
    "pending":         YELLOW,
    "skipped":         YELLOW,
    "upstream_failed": SEC_PURPLE,     # "#7030A0"
    "paused":          YELLOW_M3,      # "#FFE9AC"
    "active":          GREEN_LIGHT,    # "#AAE2C7"
    "inactive":        NEUTRAL_5,      # "#A5ABAF"
}

# =============================================================================
# Helpers
# =============================================================================


def palette(n: int) -> list[str]:
    """
    Retorna as primeiras n cores da sequência oficial de séries.

    Exemplos:
        C.palette(3)  →  ["#140A9A", "#00A7E1", "#FFC82F"]
        C.palette(6)  →  primeiras 6 cores de CHART_COLORS

    Se n > len(CHART_COLORS), as cores são cicladas.
    """
    if n <= 0:
        return []
    length = len(CHART_COLORS)
    return [CHART_COLORS[i % length] for i in range(n)]


def state_color(state: str, fallback: str = NEUTRAL_5) -> str:
    """
    Retorna a cor hex correspondente a um estado de pipeline.

    Exemplos:
        C.state_color("failed")                        →  "#FF0000"
        C.state_color("running")                       →  "#00A7E1"
        C.state_color("xyz", fallback=C.NEUTRAL_5)    →  "#A5ABAF"

    Parâmetros:
        state    — chave do estado (case-sensitive)
        fallback — cor retornada quando o estado não está mapeado
    """
    return STATE_COLORS.get(state, fallback)


def sequential_scale(
    light: str = GLORIA_BLUE_M5,
    dark: str = GLORIA_BLUE,
) -> list[list]:
    """
    Gera uma escala sequencial de 2 pontos para Plotly color_continuous_scale.

    Uso:
        scale = C.sequential_scale(light="#E2F2FF", dark="#140A9A")
        fig = px.imshow(data, color_continuous_scale=scale)
    """
    return [[0, light], [1, dark]]
