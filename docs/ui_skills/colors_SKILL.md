---
name: komatsu-ds-colors
description: >
  Identidade visual e tokens de cor do Komatsu Design System para dashboards Streamlit.
  Use esta skill sempre que precisar aplicar cores corretas em gráficos Plotly, definir
  paletas de séries, mapear estados de pipeline (success/failed/running), criar badges
  coloridos, ou consultar qualquer cor oficial do sistema. Também cobre tipografia,
  especificações de componentes visuais e a estrutura do módulo komatsu_ds.colors.
  Trigger: Komatsu Design System, cores do dashboard, paleta, tokens de cor, STATE_COLORS,
  identidade visual Komatsu, badge de estado, cor de série, cor primária, Gloria Blue.
---

# Komatsu Design System — Cores & Identidade Visual

## Módulo: `komatsu_ds.colors`

```python
from komatsu_ds import colors as C

# Uso direto
fig = px.bar(..., color_discrete_sequence=[C.GLORIA_BLUE, C.SEC_BLUE])
comp.bar_chart(..., colors=[C.RED])
comp.donut_chart(..., color_map=C.STATE_COLORS)
cor = C.state_color("failed")   # → "#FF0000"
```

---

## Paleta Principal — Gloria Blue

| Token | Hex | Uso |
|---|---|---|
| `GLORIA_BLUE_P3` | `#04121F` | Near-black, contraste extremo |
| `GLORIA_BLUE_P2` | `#08043E` | Fundo escuro profundo (uso raro) |
| `GLORIA_BLUE_P1` | `#0C065C` | Títulos de seção, bordas accent |
| **`GLORIA_BLUE`** ⭐ | **`#140A9A`** | **PRIMARY — sidebar, botões ativos, série 1** |
| `GLORIA_BLUE_M1` | `#253FC8` | Hover de botão primário |
| `GLORIA_BLUE_M2` | `#3366CC` | Links secundários |
| `GLORIA_BLUE_M3` | `#6699FF` | Accent azul claro |
| `GLORIA_BLUE_M4` | `#99CCFF` | Labels sidebar inativo, texto muted em fundo escuro |
| `GLORIA_BLUE_M5` | `#E2F2FF` | **Background de página**, seções claras |

---

## Paleta Principal — Natural Yellow

| Token | Hex | Uso |
|---|---|---|
| `YELLOW_P3` | `#665013` | Texto amarelo escuro / contraste |
| `YELLOW_P2` | `#99781C` | Ícone ou borda amarela escura |
| `YELLOW_P1` | `#CCA026` | Accent escuro |
| **`YELLOW`** ⭐ | **`#FFC82F`** | **ACCENT — série 3, highlights, warnings** |
| `YELLOW_M1` | `#FFD359` | Highlight amarelo claro |
| `YELLOW_M2` | `#FFDE82` | Tint amarelo sutil |
| `YELLOW_M3` | `#FFE9AC` | Background de badge warning |
| `YELLOW_M4` | `#FFF4D5` | Near-white amarelo |

---

## Web Orange

| Token | Hex | Uso |
|---|---|---|
| `WEB_ORANGE` | `#F7A600` | Accent laranja (usar com parcimônia) |

---

## Secundária — Blue

| Token | Hex | Uso |
|---|---|---|
| `SEC_BLUE_DARK` | `#004359` | Teal escuro, fundos profundos |
| **`SEC_BLUE`** ⭐ | **`#00A7E1`** | **Série 2, accent complementar** |
| `SEC_BLUE_LIGHT` | `#99DCF3` | Tint azul claro |

---

## Secundária — Pink & Purple

| Token | Hex | Uso |
|---|---|---|
| `SEC_PINK_DARK` | `#A5005A` | |
| `SEC_PINK` | `#E7218D` | Série 4, decorativo |
| `SEC_PINK_LIGHT` | `#F6ADD7` | |
| `SEC_PURPLE_DARK` | `#3C1A56` | |
| `SEC_PURPLE` | `#7030A0` | Série 5, decorativo |
| `SEC_PURPLE_LIGHT` | `#A568D2` | |

---

## Feedback — Positive (Green)

| Token | Hex | Uso |
|---|---|---|
| `GREEN_DARK` | `#11492E` | Texto verde escuro |
| **`GREEN`** ⭐ | **`#2BB673`** | **Delta positivo ▲, estados de sucesso** |
| `GREEN_LIGHT` | `#AAE2C7` | Background de badge success |

---

## Feedback — Negative (Red)

| Token | Hex | Uso |
|---|---|---|
| `RED_DARK` | `#660000` | Texto vermelho escuro |
| **`RED`** ⭐ | **`#FF0000`** | **Delta negativo ▼, estados de erro/falha** |
| `RED_LIGHT` | `#FF9999` | Background de badge failed |

---

## Escala de Cinzas / Neutros

| Token | Hex | Uso |
|---|---|---|
| `NEUTRAL_9` | `#2A3238` | Labels de gráfico, texto pequeno, ícones |
| `NEUTRAL_8` | `#4C5459` | Texto body/parágrafo |
| `NEUTRAL_7` | `#6E757A` | Subtexto, captions |
| `NEUTRAL_6` | `#8F969A` | Placeholder |
| `NEUTRAL_5` | `#A5ABAF` | Elementos desabilitados |
| `NEUTRAL_4` | `#C7CACD` | Bordas, divisores |
| `NEUTRAL_3` | `#E4E6E6` | Bordas claras, linhas |
| `NEUTRAL_2` | `#F6F6F6` | Backgrounds sutis |
| `NEUTRAL_1` | `#FFFFFF` | Cards, branco puro |
| `NEUTRO_3` | `#666666` | Texto de descrição/subtítulo |
| `NEUTRO_4` | `#9E9E9E` | Texto cinza claro |

---

## Sequência de Séries para Gráficos

Sempre use esta ordem para gráficos multi-série:

```python
CHART_COLORS = [
    "#140A9A",   # 1 — Gloria Blue Original  (série principal)
    "#00A7E1",   # 2 — Secondary Blue
    "#FFC82F",   # 3 — Natural Yellow
    "#E7218D",   # 4 — Secondary Pink
    "#7030A0",   # 5 — Secondary Purple
    "#0C065C",   # 6 — Gloria Blue +1 (mais escuro)
    "#99CCFF",   # 7 — Gloria Blue -4 (mais claro)
    "#F7A600",   # 8 — Web Orange
]
```

**Uso via helper:**
```python
colors = C.palette(3)   # → ["#140A9A", "#00A7E1", "#FFC82F"]
colors = C.palette(6)   # → primeiras 6 cores da sequência
```

---

## Escalas Sequenciais para Plotly

```python
# Branco → Gloria Blue (heatmaps, choropleth)
C.HEATMAP_SCALE          # [[0, "#E2F2FF"], [1, "#140A9A"]]

# Verde → Amarelo → Vermelho (performance, divergente)
C.DIVERGING_GR           # [GREEN, GREEN_LIGHT, NEUTRAL_1, RED_LIGHT, RED]

# Escala customizada
scale = C.sequential_scale(light="#E2F2FF", dark="#140A9A")
fig = px.imshow(data, color_continuous_scale=scale)
```

---

## Mapa de Estados de Pipeline

Use `STATE_COLORS` para mapear automaticamente estados do Airflow/dbt:

```python
STATE_COLORS = {
    "success":         "#2BB673",   # GREEN
    "succeeded":       "#2BB673",
    "done":            "#2BB673",
    "failed":          "#FF0000",   # RED
    "error":           "#FF0000",
    "running":         "#00A7E1",   # SEC_BLUE
    "in_progress":     "#00A7E1",
    "queued":          "#FFC82F",   # YELLOW
    "pending":         "#FFC82F",
    "skipped":         "#FFC82F",
    "upstream_failed": "#7030A0",   # SEC_PURPLE
    "paused":          "#FFE9AC",
    "active":          "#AAE2C7",
    "inactive":        "#A5ABAF",
}

# Uso em gráficos
comp.stacked_bar_chart(df, ..., color_map=C.STATE_COLORS)
comp.donut_chart(df, ..., color_map=C.STATE_COLORS)
```

**Helper de cor por estado:**
```python
cor = C.state_color("failed")              # → "#FF0000"
cor = C.state_color("running")             # → "#00A7E1"
cor = C.state_color("xyz", fallback=C.NEUTRAL_5)  # fallback para desconhecido
```

---

## Badges de Estado

Os badges usam variantes nomeadas — sempre via `comp.badge()`:

| Variante | Background | Texto | Quando usar |
|---|---|---|---|
| `"success"` | `#AAE2C7` | `#11492E` | Active, Done, Success |
| `"warning"` | `#FFE9AC` | `#665013` | Paused, Queued, Pending |
| `"error"` / `"failed"` | `#FF9999` | `#660000` | Failed, Error |
| `"running"` | `#99DCF3` | `#004359` | Running, In Progress |
| `"info"` | `#99CCFF` | `#0C065C` | Informativo neutro |
| `"neutral"` | `#F6F6F6` | `#4C5459` | Default sem estado |

```python
html = comp.badge("Active", "success")
html = comp.badge("Paused", "warning")
html = comp.badge("Failed", "error")
# Renderizar dentro de info_card ou st.markdown(..., unsafe_allow_html=True)
```

---

## Tipografia

| Elemento | Fonte | Peso | Tamanho | Cor |
|---|---|---|---|---|
| Títulos H1/H2 | Inter | 600 | — | `#0C065C` |
| Títulos de card/chart | Roboto | 600 | 15–16px | `#1B232A` |
| Valor KPI (big number) | Segoe UI | 700 | 32–36px | `#000000` |
| Label KPI | Segoe UI | 400 | 13–14px | `#000000` |
| Delta positivo | Segoe UI | 700 | 14–16px | `#2BB673` |
| Delta negativo | Segoe UI | 700 | 14–16px | `#FF0000` |
| Subtítulo / caption | Inter | 400 | 12–14px | `#9E9E9E` ou `#666666` |
| Texto sidebar (inativo) | Segoe UI | 400 | — | `#99CCFF` |

---

## Especificações de Componentes

**Card base (KPI e Chart)**
- Background: `#FFFFFF`
- Border-radius: `15px`
- Box-shadow: `0 1px 6px rgba(0,0,0,0.08)`
- Padding: `20px 16px`

**Sidebar**
- Background: `#140A9A` (Gloria Blue)
- Texto: `#FFFFFF`
- Labels inativos: `#99CCFF`

**Background da página**
- `#E2F2FF` (Gloria Blue -5)

**Gráficos Plotly**
- `paper_bgcolor`: `"white"`
- `plot_bgcolor`: `"white"`
- Gridlines: `#F0F0F0`
- Bordas de eixo: `#E4E6E6`

---

## Regras Obrigatórias

- **Nunca use cores fora deste arquivo** em dashboards Komatsu
- Sempre use `C.CHART_COLORS` ou `C.palette(n)` para séries — nunca cores ad-hoc
- Para estados de pipeline, sempre use `C.STATE_COLORS` — nunca hardcode as cores
- Manter fundo da página em `#E2F2FF` e cards em `#FFFFFF`
- Delta positivo = `#2BB673` · Delta negativo = `#FF0000` — sem exceção
