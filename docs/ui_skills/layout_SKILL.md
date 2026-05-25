---
name: komatsu-ds-layout
description: >
  Estrutura, navegação e disposição de páginas para dashboards Komatsu no Streamlit.
  Use esta skill para configurar o app (setup_page), construir a sidebar com filtros
  (sidebar context manager), criar cabeçalhos de página e seção, organizar grids de
  colunas, montar linhas de KPI cards e adicionar divisores e estados vazios.
  Deve ser consultada ANTES de qualquer outra skill ao iniciar um novo dashboard.
  Trigger: estrutura de página, sidebar, navegação, layout do dashboard, colunas,
  kpi_row, page_header, section_header, setup_page, filtros globais, multi-page app.
---

# Komatsu Design System — Layout & Estrutura de Páginas

## Módulo: `komatsu_ds.layout`

```python
from komatsu_ds import layout
```

---

## 1. Setup da Página — Sempre Primeiro

```python
layout.setup_page(
    title="Nome do Dashboard | Komatsu",
    icon="📊",                   # emoji ou URL de imagem
    layout_mode="wide",          # "wide" (default) ou "centered"
    sidebar_state="expanded",    # "expanded" (default) ou "collapsed"
)
```

> **Regra:** deve ser a **primeira** chamada Streamlit de cada arquivo de página.
> Chama `st.set_page_config()` + injeta o CSS do design system automaticamente.

---

## 2. Sidebar com Filtros

O `sidebar()` é um **context manager** que abre a sidebar estilizada e entrega
`st.sidebar` como variável. Use para adicionar filtros, navegação e status.

```python
with layout.sidebar("Nome do App", app_icon="🌀") as sb:
    # Navegação por páginas (quando não usa multi-page)
    page = sb.radio("Página", ["Overview", "Detalhes"], label_visibility="collapsed")

    # Filtros globais
    periodo = sb.selectbox("Período", ["7 dias", "14 dias", "30 dias"])
    owner   = sb.selectbox("Owner", ["Todos", "analytics", "bi-team"])
    tipos   = sb.multiselect("Tipo", ["scheduled", "manual"], default=["scheduled", "manual"])

    sb.markdown("---")
    # Status de conexão
    if conn_ok:
        sb.success("Conectado ✅")
    else:
        sb.error("Falha na conexão ❌")

    if sb.button("🔄 Atualizar", use_container_width=True):
        loader.clear_cache()
        st.rerun()
```

**Parâmetros:**

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `app_name` | str | obrigatório | Nome exibido no topo |
| `app_icon` | str | `"📊"` | Emoji do app |
| `footer` | str | `"Indicium · Data Journey"` | Texto do rodapé |

**Alternativa sem filtros — só navegação:**
```python
page = layout.sidebar_nav(
    "Nome do App",
    ["📊 Overview", "📅 Detalhe", "🚨 Alertas"],
    app_icon="📊",
)
```

---

## 3. Cabeçalho de Página

```python
layout.page_header(
    title="Airflow Monitoring",
    subtitle="Visão geral de saúde das pipelines",   # opcional
    source_hint="fct_dag_runs · dim_dags",            # opcional — exibe em <code>
)
```

Renderiza `H1` + subtítulo em cinza + hint de fonte em código. Deve vir logo após o bloco de carregamento de dados.

---

## 4. Cabeçalho de Seção

```python
layout.section_header("KPIs do Período", "📈")
layout.section_header("Runs Falhados — Detalhamento", "📋")
layout.section_header("Tasks desta DAG", "🔧")
```

Separador visual interno à página. Fonte Inter 600, cor `#0C065C`, borda inferior azul.

---

## 5. Linha de KPI Cards — kpi_row

Monta automaticamente N colunas e renderiza um KPI card por item.

```python
layout.kpi_row([
    {"label": "Taxa de Sucesso",  "value": "98.2%",  "delta": "+1.3%",  "icon": "✅"},
    {"label": "Total de Runs",    "value": "1.234",   "neutral": True,   "icon": "🔄"},
    {"label": "Falhas",           "value": "22",      "delta": "-5",     "icon": "❌"},
    {"label": "DAGs Ativas",      "value": "12",      "neutral": True,   "icon": "🟢"},
    {"label": "Duração Média",    "value": "3m 42s",  "neutral": True,   "icon": "⏱️"},
])
```

**Chaves do dict:**

| Chave | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `label` | str | ✅ | Texto acima do valor |
| `value` | str | ✅ | Valor principal (big number) |
| `delta` | str | — | Variação (▲ verde se não começa com `-`, ▼ vermelho se começa) |
| `icon` | str | — | Emoji exibido acima do label |
| `neutral` | bool | — | `True` → delta sem cor (cinza) |

**Versão compacta** (para 6+ cards ou espaço reduzido):
```python
layout.kpi_row(cards, compact=True)
```

---

## 6. Linha de KPI Cards Horizontal — kpi_row_horizontal

Cards mais largos com ícone grande à esquerda — ideal para painéis de alertas.

```python
layout.kpi_row_horizontal([
    {"icon": "🔴", "label": "Runs com Falha",  "value": "7",    "delta": "3.2% do total"},
    {"icon": "⚠️", "label": "DAGs Afetadas",   "value": "4",    "neutral": True},
    {"icon": "🔧", "label": "Tasks Falhadas",  "value": "128",  "delta": "12.1% das tasks"},
    {"icon": "📉", "label": "Máx. Falhas/DAG", "value": "9",    "neutral": True},
])
```

---

## 7. Grids de Colunas

```python
# 2 colunas — proporção configurável
col_l, col_r = layout.columns_2()                  # 50% / 50%
col_l, col_r = layout.columns_2(ratio=(2, 1))      # 66% / 33%
col_l, col_r = layout.columns_2(ratio=(3, 1))      # 75% / 25%

# 3 colunas
c1, c2, c3 = layout.columns_3()                   # iguais
c1, c2, c3 = layout.columns_3(ratio=(2, 1, 1))    # proporção personalizada

# 4 colunas
c1, c2, c3, c4 = layout.columns_4()

# N colunas iguais (qualquer número)
cols = layout.columns_n(6)                         # 6 colunas iguais
cols = layout.columns_n(4, gap="large")

# Espaçamento: "small" | "medium" (default) | "large"
```

**Uso dentro de colunas:**
```python
col_l, col_r = layout.columns_2(ratio=(2, 1))
with col_l:
    comp.render_chart(fig1, title="Gráfico principal")
with col_r:
    comp.render_chart(fig2, title="Detalhe")
```

---

## 8. Divisor Horizontal

```python
layout.divider()
```

Linha horizontal sutil (`#E4E6E6`). Use para separar blocos dentro de uma página.

---

## 9. Barra de Filtros Inline

Context manager que envolve filtros horizontais em um card branco:

```python
with layout.filter_bar():
    fc1, fc2, fc3 = st.columns([1, 1, 2])
    with fc1:
        periodo = st.selectbox("Período", ["7d", "14d", "30d"])
    with fc2:
        owner = st.selectbox("Owner", owners)
    with fc3:
        tipos = st.multiselect("Tipo", tipos_lista, default=tipos_lista)
```

---

## 10. Estado Vazio

```python
layout.empty_state(
    message="Nenhuma falha registrada no período! 🎉",
    icon="✅",
)

# Padrão sem argumentos:
layout.empty_state()
# → "Nenhum dado encontrado para os filtros selecionados." + ícone 🔍
```

---

## Estrutura Multi-Page (Streamlit Cloud)

Para apps com múltiplas páginas, cada arquivo deve:

```python
# topo de CADA arquivo de página
layout.setup_page("Título da Página | Komatsu", icon="📊")

days, run_types, conn_ok, conn_msg = render_sidebar()   # via utils.py
```

**Estrutura de arquivos:**
```
Home.py                   ← página principal
utils.py                  ← render_sidebar(), load_and_filter_data(), helpers
dag_monitoring_loader.py  ← conexão Snowflake e queries
komatsu_ds/               ← design system
pages/
  1_Nome_Pagina.py        ← Streamlit detecta automaticamente
  2_Outra_Pagina.py
  3_Terceira_Pagina.py
```

> O Streamlit usa o nome do arquivo como label da página na navegação lateral.
> Prefixo numérico (`1_`, `2_`) define a ordem.

---

## Padrão Completo de uma Página

```python
# 1. Imports
from komatsu_ds import colors as C, components as comp, layout
from utils import render_sidebar, render_owner_filter, load_and_filter_data

# 2. Setup (SEMPRE PRIMEIRO)
layout.setup_page("Título | Komatsu", icon="📊")

# 3. Sidebar + conexão
days, run_types, conn_ok, conn_msg = render_sidebar()
if not conn_ok:
    st.error(f"Falha na conexão: {conn_msg}")
    st.stop()

# 4. Carregamento de dados
dags_df, tasks_df, runs_f, ti_f = load_and_filter_data(days, run_types)
sel_owner = render_owner_filter(dags_df)
if sel_owner != "Todos":
    dags_df, tasks_df, runs_f, ti_f = load_and_filter_data(days, run_types, sel_owner)

# 5. Header
layout.page_header("Título", "Subtítulo", source_hint="tabela · tabela")

# 6. KPIs
layout.section_header("Métricas", "📈")
layout.kpi_row([...])
layout.divider()

# 7. Gráficos em grid
col1, col2 = layout.columns_2(ratio=(2, 1))
with col1:
    comp.render_chart(fig, title="...")
with col2:
    comp.render_chart(fig2, title="...")
```
