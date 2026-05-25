---
name: komatsu-ds-components
description: >
  Catálogo completo de gráficos, tabelas, KPI cards e componentes visuais do
  Komatsu Design System para Streamlit. Use esta skill para escolher e implementar
  qualquer visualização: barras, linhas, áreas, donut, scatter, heatmap, histograma,
  funil, gauge, tabelas, KPI cards (padrão/compacto/horizontal), badges de estado
  e info cards de metadados. Todas as funções retornam figuras Plotly pré-estilizadas
  ou renderizam HTML seguindo o design system Komatsu.
  Trigger: gráfico, chart, tabela, KPI card, badge, visualização, bar chart, donut,
  heatmap, scatter, linha, área, histograma, funil, gauge, render_chart, render_table.
---

# Komatsu Design System — Catálogo de Componentes

## Módulo: `komatsu_ds.components`

```python
from komatsu_ds import components as comp
from komatsu_ds import colors as C
```

**Padrão de uso:** todas as funções de gráfico **retornam** uma `go.Figure` já configurada.
Use `comp.render_chart(fig, title, subtitle)` para exibir com o card branco do DS.

```python
fig = comp.bar_chart(df, x="mes", y="valor")
comp.render_chart(fig, title="Vendas por Mês", subtitle="Últimos 12 meses")
```

---

## Gráficos — Catálogo Completo

---

### `bar_chart` — Barras Verticais ou Horizontais

**Quando usar:** comparar valores entre categorias; rankings; top N.

```python
fig = comp.bar_chart(
    df,
    x="categoria",          # coluna do eixo X (ou Y se horizontal)
    y="valor",              # coluna do eixo Y (ou X se horizontal)
    horizontal=False,       # True para barras horizontais
    color_col=None,         # coluna para colorir por grupo (opcional)
    color_map=None,         # dict {valor: cor_hex} (opcional)
    colors=None,            # lista de cores ex: [C.RED] ou [C.GLORIA_BLUE]
    height=320,
)
```

**Exemplos:**
```python
# Ranking simples
fig = comp.bar_chart(df, x="dag", y="falhas", horizontal=True, colors=[C.RED])

# Por grupo com cor fixa
fig = comp.bar_chart(df, x="data", y="count", colors=[C.GLORIA_BLUE])

# Por grupo com mapa de cores
fig = comp.bar_chart(df, x="tipo", y="count", color_col="estado", color_map=C.STATE_COLORS)
```

---

### `stacked_bar_chart` — Barras Empilhadas

**Quando usar:** volume total dividido por estado/categoria ao longo do tempo.

```python
fig = comp.stacked_bar_chart(
    df,
    x="dt_run_date",        # eixo X (geralmente data)
    y="count",              # eixo Y (contagem)
    color_col="cat_dag_run_state",  # coluna que define as pilhas
    color_map=C.STATE_COLORS,       # mapa de cores por estado
    height=300,
)
```

**Exemplo — runs por dia com cor de estado:**
```python
daily = runs_f.groupby(["dt_run_date", "cat_dag_run_state"]).size().reset_index(name="count")
fig = comp.stacked_bar_chart(daily, x="dt_run_date", y="count",
                              color_col="cat_dag_run_state", color_map=C.STATE_COLORS)
comp.render_chart(fig, title="Runs por Dia — Sucesso vs Falha")
```

---

### `line_chart` — Linha Simples ou Multi-série

**Quando usar:** tendências ao longo do tempo; comparação de séries temporais.

```python
fig = comp.line_chart(
    df,
    x="mes",
    y="valor",              # string (1 série) ou list[str] (múltiplas)
    markers=True,           # pontos nos dados
    title="",               # título interno (opcional — prefira render_chart)
    height=300,
)
```

**Exemplos:**
```python
# Série única
fig = comp.line_chart(df, x="data", y="taxa_sucesso")

# Multi-série
fig = comp.line_chart(df, x="semana", y=["dag_a", "dag_b", "dag_c"])
```

---

### `area_chart` — Área Preenchida

**Quando usar:** evolução temporal de categorias; tendências empilhadas.

```python
fig = comp.area_chart(
    df,
    x="dt_run_date",
    y="count",
    color_col="cat_instance_state",   # opcional — uma área por valor
    color_map=C.STATE_COLORS,         # opcional
    height=280,
)
```

**Exemplo — evolução de tasks por estado:**
```python
daily_ti = ti_f.groupby(["dt_run_date", "cat_instance_state"]).size().reset_index(name="count")
fig = comp.area_chart(daily_ti, x="dt_run_date", y="count",
                      color_col="cat_instance_state", color_map=C.STATE_COLORS)
comp.render_chart(fig, title="Tasks por Estado ao Longo do Tempo")
```

---

### `donut_chart` — Rosca (Donut)

**Quando usar:** proporções e distribuições; partes de um todo; máx. 6–8 categorias.

```python
fig = comp.donut_chart(
    df,
    names="categoria",      # coluna com rótulos das fatias
    values="count",         # coluna com valores
    color_map=None,         # dict opcional {nome: cor_hex}
    hole=0.5,               # espessura do buraco (0–1); 0 = pizza sólida
    height=280,
)
```

**Exemplos:**
```python
# Distribuição de estados (com mapa de cores)
fig = comp.donut_chart(state_cts, names="estado", values="count",
                       color_map=C.STATE_COLORS)

# Distribuição por owner (sem mapa — usa paleta automática)
fig = comp.donut_chart(owner_df, names="owner", values="count", hole=0.4)

# Pizza sólida
fig = comp.donut_chart(df, names="tipo", values="total", hole=0.0)
```

---

### `scatter_chart` — Dispersão

**Quando usar:** relação entre duas variáveis numéricas; timeline de eventos com duração.

```python
fig = comp.scatter_chart(
    df,
    x="ts_run_start",       # eixo X
    y="vl_duration_seconds",# eixo Y
    color_col="cat_dag_run_state",  # opcional — cor por categoria
    color_map=C.STATE_COLORS,       # opcional
    size_col=None,          # opcional — coluna para tamanho dos pontos
    height=300,
)
```

**Exemplo — timeline de runs:**
```python
fig = comp.scatter_chart(dag_runs.sort_values("ts_run_start"),
                         x="ts_run_start", y="vl_duration_seconds",
                         color_col="cat_dag_run_state", color_map=C.STATE_COLORS)
comp.render_chart(fig, title="Timeline de Runs — Estado × Duração")
```

---

### `histogram` — Histograma de Distribuição

**Quando usar:** distribuição de uma variável numérica (duração, latência, tamanho).

```python
fig = comp.histogram(
    series,                 # pd.Series com os valores
    bins=20,                # número de intervalos
    color=C.GLORIA_BLUE,    # cor das barras
    title="",               # título interno (opcional)
    height=300,
)
```

**Exemplo — distribuição de duração de runs:**
```python
dur_min = dag_runs["vl_duration_seconds"].dropna() / 60
dur_min.name = "Duração (min)"
fig = comp.histogram(dur_min, bins=15)
comp.render_chart(fig, title="Distribuição de Duração (min)")
```

---

### `heatmap` — Mapa de Calor

**Quando usar:** padrões 2D (DAG × dia da semana, hora × dia, categoria × período).

```python
fig = comp.heatmap(
    pivot_df,               # DataFrame pivot (linhas = y, colunas = x)
    color_scale=None,       # escala Plotly; default = C.HEATMAP_SCALE
    title="",               # título interno (opcional)
    height=400,
    fmt=".1f",              # formato dos valores nas células
)
```

**Exemplo — duração média por DAG × dia da semana:**
```python
hm = ti_f.groupby(["pk_dag_id", "day_of_week"])["vl_duration_seconds"].mean().reset_index()
hm["duration_min"] = hm["vl_duration_seconds"] / 60
pivot = hm.pivot_table(index="pk_dag_id", columns="day_of_week", values="duration_min")
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])

fig = comp.heatmap(pivot, height=max(300, len(pivot) * 34))
comp.render_chart(fig, title="Duração Média por DAG × Dia (min)")
```

---

### `funnel_chart` — Funil

**Quando usar:** taxas de conversão; etapas de pipeline; drop-off entre fases.

```python
fig = comp.funnel_chart(
    df,
    stage_col="etapa",      # coluna com nome das etapas
    value_col="contagem",   # coluna com valores
    title="",
    height=320,
)
```

---

### `gauge_chart` — Gauge (Velocímetro)

**Quando usar:** KPI único com target e faixas de performance.

```python
fig = comp.gauge_chart(
    value=87.3,             # valor atual (float)
    title="Taxa de Sucesso",
    min_val=0,
    max_val=100,
    thresholds=[70, 90],    # [limite_vermelho, limite_amarelo] → acima = verde
    height=300,
)
```

---

## Renderizadores

---

### `render_chart` — Exibir Gráfico no Card

Envolve qualquer `go.Figure` no card branco do design system.

```python
comp.render_chart(
    fig,                    # go.Figure retornado por qualquer função de gráfico
    title="Título do Card", # exibido acima do gráfico
    subtitle="Subtítulo",   # opcional — em cinza abaixo do título
    height=None,            # sobrescreve a altura da figura se informado
)
```

> **Sempre use `render_chart`** em vez de `st.plotly_chart()` diretamente.

---

### `render_table` — Tabela Estilizada

```python
comp.render_table(
    df,                     # pd.DataFrame a exibir
    height=400,             # altura em pixels
    hide_index=True,        # ocultar índice (default True)
)
```

**Exemplo:**
```python
comp.render_table(
    task_summary[["Task", "Operator", "Sucesso (%)", "Falhas", "Retries"]],
    height=320,
)
```

---

## KPI Cards

---

### `kpi_card` — Card KPI Padrão (Vertical)

```python
comp.kpi_card(
    label="Taxa de Sucesso",
    value="98.2%",
    delta="+1.3%",          # positivo = verde ▲ | negativo (começa com -) = vermelho ▼
    icon="✅",              # emoji acima do label
    neutral=False,          # True → delta sem cor (cinza)
)
```

> **Prefira `layout.kpi_row([...])` para múltiplos cards** — cria as colunas automaticamente.

---

### `kpi_card_compact` — Card KPI Compacto

Fonte menor — use quando há 6 ou mais cards na linha.

```python
comp.kpi_card_compact(
    label="Taxa de Sucesso",
    value="98.2%",
    delta="+1.3%",
    neutral=False,
)
```

---

### `kpi_card_horizontal` — Card KPI com Ícone à Esquerda

Ícone grande à esquerda, label + valor à direita — ideal para painéis de alerta.

```python
comp.kpi_card_horizontal(
    icon="🔴",
    label="Runs com Falha",
    value="7",
    delta="3.2% do total",
    neutral=False,
)
```

---

## Outros Componentes

---

### `badge` — Badge de Estado

Retorna HTML de um badge colorido. Use dentro de `info_card` ou `st.markdown`.

```python
html = comp.badge("Active",  "success")   # verde
html = comp.badge("Paused",  "warning")   # amarelo
html = comp.badge("Failed",  "error")     # vermelho
html = comp.badge("Running", "running")   # azul
html = comp.badge("Info",    "info")      # azul claro
html = comp.badge("—",       "neutral")   # cinza

# Renderizar diretamente
st.markdown(comp.badge("Active", "success"), unsafe_allow_html=True)
```

---

### `info_card` — Card de Metadados Key-Value

Card branco com título e pares chave-valor. Ideal para detalhes de uma entidade.

```python
comp.info_card(
    title="Detalhes da DAG",
    items={
        "Status":        comp.badge(dag["cat_status"], "success"),  # aceita HTML
        "Owner":         dag["nm_owners"],
        "Schedule":      dag["desc_timetable"],
        "Próximo Run":   "15/04 10:00",
        "Nº de Tasks":   "8",
        "Total de Runs": "42",
    }
)
```

---

### `section_header` — Cabeçalho de Seção (via components)

```python
comp.section_header("KPIs de Tasks", "🔧")
```

> Idêntico a `layout.section_header()` — disponível em ambos os módulos por conveniência.

---

## Guia de Escolha de Gráfico

| Necessidade | Gráfico | Função |
|---|---|---|
| Comparar N categorias (ranking) | Barras horizontais | `bar_chart(..., horizontal=True)` |
| Comparar N categorias (vertical) | Barras verticais | `bar_chart(...)` |
| Volume por estado ao longo do tempo | Barras empilhadas | `stacked_bar_chart(...)` |
| Tendência de uma métrica | Linha | `line_chart(...)` |
| Tendência de múltiplas séries | Linha multi-série | `line_chart(..., y=[...])` |
| Evolução empilhada de categorias | Área | `area_chart(...)` |
| Proporções / partes de um todo | Rosca | `donut_chart(...)` |
| Relação entre 2 variáveis | Dispersão | `scatter_chart(...)` |
| Distribuição de uma variável | Histograma | `histogram(...)` |
| Padrão 2D (categorias × tempo) | Heatmap | `heatmap(pivot_df)` |
| Etapas com drop-off | Funil | `funnel_chart(...)` |
| KPI único com meta | Velocímetro | `gauge_chart(...)` |
| Exibir dados tabulares | Tabela | `render_table(df)` |
| Métrica numérica destacada | KPI Card | `layout.kpi_row([...])` |
| Status de uma entidade | Badge | `comp.badge(...)` |
| Metadados de uma entidade | Info Card | `comp.info_card(...)` |

---

## Regras do Design System

- **Sempre use `render_chart(fig, title, subtitle)`** — nunca `st.plotly_chart()` diretamente
- **Sempre use `layout.kpi_row([...])`** para múltiplos KPI cards — nunca crie colunas manualmente
- **Para estados de pipeline**, passe `color_map=C.STATE_COLORS` — nunca hardcode cores
- **Para séries sem mapa**, omita `colors` — o DS usa `C.CHART_COLORS` automaticamente
- **`horizontal=True`** em `bar_chart` quando os rótulos das categorias são longos (nomes de DAG, tabela, etc.)
- **Altura padrão:** 280–320px para gráficos secundários, 300–340px para principais
- **Heatmap:** `height=max(300, len(pivot) * 34)` para escalar com o número de linhas
