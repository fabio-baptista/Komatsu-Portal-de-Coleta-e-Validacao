# UI Style Guide — Portal de Coleta e Validação de Forecast
> Referência oficial de identidade visual para implementação Streamlit.
> Referência visual antiga removida. A próxima refatoração de UI deve seguir as skills oficiais em docs/ui_skills/.

---

## 1. Paleta de Cores Oficial

### Cores primárias

| Token | Hex | Nome |
|---|---|---|
| `--navy` | `#002B5C` | Komatsu Navy |
| `--yellow` | `#FFCD00` | Komatsu Yellow |
| `--gray` | `#F4F5F7` | Komatsu Gray (background) |
| `--border-navy` | `#001D3D` | Navy escuro (gradiente/bordas) |
| `--text` | `#1A1A1A` | Texto base |

### Cores de suporte

| Uso | Hex / Tailwind equiv. |
|---|---|
| Fundo de cards e painéis | `#FFFFFF` |
| Bordas gerais | `#E5E7EB` (gray-200) |
| Bordas suaves | `#F3F4F6` (gray-100) |
| Labels e textos secundários | `#9CA3AF` (gray-400) |
| Fundo de inputs / thead | `#F9FAFB` (gray-50) |

### Gradiente oficial

```css
background: linear-gradient(135deg, #002B5C 0%, #001D3D 100%);
```
Usado no topo da sidebar e em elementos decorativos.

### Cores de status (badges)

| Status | Background | Texto | Label exibido |
|---|---|---|---|
| valid | `#DCFCE7` | `#15803D` | Válido/Ativo |
| invalid | `#FEE2E2` | `#B91C1C` | Inválido |
| replaced | `#DBEAFE` | `#1D4ED8` | Substituído |
| canceled | `#F3F4F6` | `#374151` | Cancelado |
| processed | `rgba(0,43,92,0.1)` | `#002B5C` | Processado |
| pending | `#EFF6FF` | `#60A5FA` | Pendente |

---

## 2. Regras de Uso das Cores

- **Amarelo (`#FFCD00`)** → exclusivo para CTAs principais, logo KOMATSU e badges de ação. Nunca usar como fundo de texto longo.
- **Navy (`#002B5C`)** → fundo do header, topo da sidebar, botões primários, textos de valor nos cards. É a cor dominante da marca.
- **Gray (`#F4F5F7`)** → único background permitido para o body da aplicação. Nunca usar branco como fundo de página.
- **Branco (`#FFFFFF`)** → exclusivo para cards, painéis, tabelas e modais sobre o fundo gray.
- **Vermelho** → apenas em estado de erro (badges, alertas, texto de linha inválida). Nunca usar como cor de ação.
- **Verde** → apenas em estado de sucesso/válido. Nunca usar como cor decorativa.
- **Textos sobre navy** → sempre branco puro ou `branco/60` para informações secundárias.
- **Textos sobre amarelo** → sempre navy (`#002B5C`). Nunca preto ou branco.

---

## 3. Layout Principal do App

```
┌──────────────────────────────────────────────────────────────┐
│  SIDEBAR (240px, fixa, lado esquerdo)                         │
│  bg: white | border-right: #E5E7EB                           │
├──────────────────────────────────────────────────────────────┤
│  HEADER (64px, fixo, topo)                                   │
│  bg: #002B5C | margem-esquerda: 240px                        │
├──────────────────────────────────────────────────────────────┤
│  MAIN CONTENT                                                │
│  bg: #F4F5F7 | padding: 24px | margem-esquerda: 240px        │
│  espaçamento entre seções: 24px                              │
├──────────────────────────────────────────────────────────────┤
│  FOOTER (32px)                                               │
│  bg: #F3F4F6 | border-top: #E5E7EB | dentro do main         │
└──────────────────────────────────────────────────────────────┘
```

### Tipografia

| Elemento | Família | Peso | Tamanho |
|---|---|---|---|
| Logo "KOMATSU" | Outfit | 800–900 | 24–32px |
| Títulos de página/seção | Inter | 700 | 18–24px |
| Labels de campo | Inter | 700 | 10px uppercase |
| Corpo / textos gerais | Inter | 400–500 | 13–14px |
| Texto técnico / código | monospace | 700 | 10–11px |
| Rodapé | Inter | 500 | 10px |

---

## 4. Estrutura do Header / Topbar

- **Altura:** 64px
- **Background:** `#002B5C`
- **Posição:** sticky no topo, offset esquerdo de 240px (largura da sidebar)
- **Borda inferior:** `1px solid #001D3D`

### Lado esquerdo
1. Texto `"KOMATSU"` — fonte Outfit, extrabold, `#FFCD00`, tracking tight
2. Separador vertical — `1px` `rgba(255,255,255,0.2)`, altura 24px
3. Título da página atual — Inter, `font-medium`, branco, 18px

### Lado direito
1. Bloco de usuário:
   - Nome: `text-white text-xs font-semibold`, alinhado à direita
   - Email: `rgba(255,255,255,0.6) text-[10px]`
2. Avatar circular:
   - Tamanho: 40px
   - Background: `#FFCD00`
   - Iniciais em navy, fonte bold
   - Borda: `ring-2 ring-white/10`

---

## 5. Estrutura da Sidebar

- **Largura:** 240px, fixa, `height: 100vh`
- **Background:** branco
- **Borda direita:** `1px solid #E5E7EB`
- **Z-index:** acima do conteúdo principal

### Zona 1 — Logo (topo)
```
background: #002B5C (ou gradiente navy)
padding: 24px
"KOMATSU" → Outfit, font-black, #FFCD00, text-3xl
```

### Zona 2 — Navegação (meio, flex-grow)
```
padding: 16px
space-y: 4px

Label de seção:
  10px | bold | gray-400 | uppercase | tracking-widest

Item de menu inativo:
  flex + ícone (18px) + texto (14px)
  text: gray-600
  hover: bg-gray-50
  border-radius: 6px
  padding: 8px 12px

Item de menu ativo:
  bg: #F4F5F7 (komatsu-gray)
  text: #002B5C | font-bold
  shadow-sm
```

### Zona 3 — Rodapé (baixo)
```
background: rgba(249,250,251,0.5)
border-top: #F3F4F6
padding: 16px

Widget "Janela do Ciclo":
  bg: #EFF6FF | border: #DBEAFE | rounded-lg | padding: 12px
  Label: 10px bold #1E40AF uppercase
  Progress bar: bg-gray-200 → fill #002B5C, altura 6px, rounded
  Percentual: 10px bold #1E40AF
  Data encerramento: 10px italic #2563EB

Botão Sair:
  flex + ícone LogOut + "Sair do Portal"
  text: red-500 | hover: bg-red-50
  font-semibold | text-sm | rounded-md | padding: 8px 12px
```

---

## 6. Estilo dos Cards

### Card de métrica simples
```
background: white
border: 1px solid #E5E7EB
border-radius: 12px
padding: 16px
shadow: 0 1px 3px rgba(0,0,0,0.05)

  Label: 10px | bold | gray-400 | uppercase | margin-bottom: 8px
  Valor: 18px | bold | #002B5C
  Detalhe: 10px | gray-400 | margin-top: 4px
```

### Card de KPI (admin) — variante com accent inferior
```
Igual ao card simples +
border-bottom: 2px solid #002B5C
Valor: 24px | bold | #002B5C
```

### Card de ação rápida (dashed)
```
border: 2px dashed #E5E7EB
border-radius: 12px
padding: 24px
text-align: center
cursor: pointer

hover:
  border-color: #FFCD00
  background: rgba(255,205,0,0.05)

Ícone container:
  círculo 48px | bg: #002B5C | text: white | rounded-full
  hover: scale(1.1)

Label: text-sm | font-bold | #002B5C
```

### Card navy (informativo/aviso)
```
background: #002B5C
border-radius: 12px
padding: 24px
color: white

Título: font-bold | 18px | com ícone #FFCD00
Texto: 14px | opacity: 0.8 | line-height: 1.6
Decoração: ícone grande opacity-10 blur-xl no canto inferior direito

Seção inferior:
  border-top: rgba(255,255,255,0.1)
  Label: 10px uppercase #FFCD00 tracking-widest
  Valor: 20px font-display
```

### Card de sumário com destaque amarelo
```
Igual ao card simples +
border-bottom: 4px solid #FFCD00
```

---

## 7. Estilo das Tabelas

### Estrutura geral
```
Container:
  background: white
  border: 1px solid #E5E7EB
  border-radius: 12px
  overflow: hidden

Cabeçalho da seção (acima da <table>):
  padding: 24px
  border-bottom: 1px solid #F3F4F6
  display: flex | justify-content: space-between | align-items: center
  background: rgba(249,250,251,0.5)  [opcional]

<thead>:
  background: #F9FAFB
  border-bottom: 1px solid #F3F4F6
  th: 10px | bold | gray-400 | uppercase | tracking-widest | padding: 16px 24px

<tbody>:
  font-size: 14px
  rows divididas por: border-bottom 1px solid #F3F4F6
  row hover: background #F9FAFB
  td: padding: 16px 24px
```

### Variantes de linha
```
Accent hover (tabelas de dados):
  border-left: 4px solid transparent
  hover: border-left-color: #002B5C  [admin]
  hover: border-left-color: #60A5FA  [trusted data]

Linha de erro:
  td com erro: text-red-600 | font-medium

Linha de código/ID:
  font-mono | font-bold | text-blue-600

Linha de valores técnicos (trusted):
  font-mono | text-[11px] | italic
```

### Valores especiais em células
```
Upload ID: font-mono bold blue-600
Versão: badge cinza claro (px-2 py-0.5 bg-gray-100 rounded text-[10px] font-bold)
Quantidade numérica: text-lg bold komatsu-navy
Período: font-semibold komatsu-navy
Data: text-xs gray-400
Erros: red-500 bold (se > 0) | gray-200 "-" (se 0)
```

---

## 8. Estilo dos Filtros

### Container de filtros
```
background: white
border: 1px solid #E5E7EB
border-radius: 12px
padding: 24px
margin-bottom: 24px
```

### Campos individuais
```
Label: 10px | bold | gray-400 | uppercase | margin-bottom: 4px

Select / Input:
  background: #F9FAFB
  border: 1px solid #E5E7EB
  border-radius: 8px
  padding: 8px 12px
  font-size: 14px
  color: gray-600
  focus: outline none | ring 1px #002B5C

Botão "Filtrar":
  background: #002B5C
  color: white
  font-bold
  border-radius: 8px
  shadow: 0 4px 6px rgba(0,0,0,0.1)
  hover: opacity 90%
  active: scale(0.95)
  ícone Search inline
```

### Search inline (dentro do cabeçalho de tabela)
```
Input com ícone Search posicionado absolutamente à esquerda
padding-left: 40px
background: #F9FAFB
border: 1px solid #E5E7EB
border-radius: 8px
font-size: 14px
```

---

## 9. Estilo dos Botões

### Primário amarelo (CTA principal)
```css
background: #FFCD00;
color: #002B5C;
font-weight: 700;
border-radius: 12px;
padding: 12px 32px;
box-shadow: 0 4px 6px rgba(0,0,0,0.1);
hover: filter brightness(0.95);
active: transform scale(0.95);
```

### Primário navy
```css
background: #002B5C;
color: white;
font-weight: 700;
border-radius: 12px;
padding: 12px 32px;
box-shadow: 0 4px 6px rgba(0,0,0,0.1);
hover: opacity 90%;
active: transform scale(0.95);
```

### Outline navy
```css
border: 2px solid #002B5C;
color: #002B5C;
background: transparent;
font-weight: 700;
border-radius: 12px;
padding: 12px 24px;
hover: background #002B5C; color white;
```

### Secundário (ghost)
```css
background: white;
border: 1px solid #E5E7EB;
color: #9CA3AF;
font-weight: 700;
border-radius: 6px;
padding: 10px 24px;
hover: color #002B5C; border-color #002B5C;
```

### Destrutivo (cancelar envio)
```css
color: #F87171;
background: transparent;
font-weight: 700;
font-size: 10px;
text-transform: uppercase;
text-decoration: underline;
text-underline-offset: 4px;
hover: color #DC2626;
```

### Ghost ícone (filter, refresh)
```css
padding: 8px;
border: 1px solid #E5E7EB;
border-radius: 8px;
color: #9CA3AF;
hover: background #F3F4F6;
```

### Notificar (admin, pequeno)
```css
background: #FFCD00;
color: #002B5C;
border-radius: 8px;
font-size: 10px;
font-weight: 700;
text-transform: uppercase;
padding: 4px 12px;
box-shadow: 0 1px 2px rgba(0,0,0,0.05);
active: scale(0.95);
```

### Botão de login — Fornecedor
```css
background: #FFCD00;
color: #002B5C;
font-weight: 900;
font-size: 12px;
text-transform: uppercase;
letter-spacing: 0.1em;
padding: 16px 24px;
border-radius: 6px;
width: 100%;
```

### Botão de login — Admin
```css
background: white;
border: 1px solid #E5E7EB;
color: #9CA3AF;
font-weight: 700;
font-size: 12px;
text-transform: uppercase;
letter-spacing: 0.1em;
padding: 12px 24px;
border-radius: 6px;
width: 100%;
hover: color #002B5C; border-color #002B5C;
```

---

## 10. Estilo dos Badges de Status

### Formato base
```css
display: inline-block;
padding: 4px 8px;
border-radius: 9999px;  /* rounded-full */
font-size: 12px;
font-weight: 600;
white-space: nowrap;
```

### Por status

```css
/* valid */
.badge-valid    { background: #DCFCE7; color: #15803D; }

/* invalid */
.badge-invalid  { background: #FEE2E2; color: #B91C1C; }

/* replaced */
.badge-replaced { background: #DBEAFE; color: #1D4ED8; }

/* canceled */
.badge-canceled { background: #F3F4F6; color: #374151; }

/* processed */
.badge-processed { background: rgba(0,43,92,0.1); color: #002B5C; }

/* pending */
.badge-pending  { background: #EFF6FF; color: #60A5FA; }
```

### Badge de versão (número)
```css
display: inline-flex;
width: 24px; height: 24px;
align-items: center; justify-content: center;
background: #F3F4F6;
border-radius: 4px;
font-size: 12px;
font-weight: 700;
```

---

## 11. Estilo de Alertas de Erro / Sucesso

### Alerta de erro (arquivo inválido)
```
background: #FEF2F2
border: 1px solid #FECACA
border-radius: 16px
padding: 24px
display: flex | gap: 16px

Ícone container:
  background: #FEE2E2
  color: #DC2626
  border-radius: 9999px
  padding: 12px

Título: #991B1B | font-bold | 18px
Mensagem: #B91C1C | 14px
```

### Alerta de sucesso
```
background: #F0FDF4
border: 1px solid #BBF7D0
border-radius: 16px
padding: 24px
display: flex | gap: 16px

Ícone container:
  background: #DCFCE7
  color: #16A34A
  border-radius: 9999px
  padding: 12px

Título: #166534 | font-bold | 18px
Mensagem: #15803D | 14px
```

### Banner informativo MVP (nota de contexto)
```
background: rgba(255,205,0,0.1)
border: 1px solid rgba(255,205,0,0.2)
border-radius: 16px
padding: 24px

Prefixo: "NOTA MVP:" | font-extrabold | uppercase | #002B5C
Texto: 12px | #002B5C | font-medium | line-height: 1.6
```

### Banner SQL / rastreabilidade
```
background: #002B5C
border-radius: 16px
padding: 16px

Título: 10px | uppercase | bold | rgba(255,255,255,0.6) | tracking-widest
Code block:
  background: rgba(0,0,0,0.2)
  border-radius: 6px
  padding: 8px
  font-family: monospace
  font-size: 10px
  color: rgba(255,255,255,0.8)
  word-break: break-all
```

---

## 12. Telas Previstas — Perfil Fornecedor

### 1. Login
- Cartão centralizado na tela, máx. 448px
- Topo do cartão: bloco navy com "KOMATSU" amarelo + subtítulo "Portal de Coleta e Validação"
- Campos: email + senha (bg gray-50, border gray-200)
- Dois botões: "Entrar como Fornecedor" (amarelo) e "Acesso Administrativo" (branco/outline)
- Rodapé: © Komatsu | Uso Restrito | TI Operações

### 2. Supplier Home (Dashboard)
- Saudação: "Olá, {nome do fornecedor}" + subtítulo
- 4 cards de métrica: Último Envio, Status Atual, Versão do Forecast, Linhas Processadas
- Grid 3 ações rápidas (dashed): Enviar Forecast, Baixar Template, Ver Histórico
- Card navy: Aviso de Privacidade + versão do sistema

### 3. Supplier Upload (Submeter Forecast)
- Largura máxima: 896px, centralizado
- 2 campos de contexto (read-only): Tipo de Relatório + Período de Referência
- Área de drag-and-drop: border dashed grossa, ícone navy, hover amarelo, limite 50MB
- Seção de validações automáticas: grid de 9 itens com bullet verde
- Botões de ação: "Cancelar" (ghost) + "Validar Forecast" (amarelo)

### 4. Supplier Errors (Relatório de Erros)
- Banner de erro vermelho: ícone X + título + contagem de erros
- Tabela de inconsistências: Linha | Coluna | Valor | Erro | Orientação
- Coluna "Valor": badge cinza com borda (valor ou "(vazio)")
- Coluna "Erro": text-red-600
- Coluna "Orientação": 10px uppercase italic gray-500
- Botão download: "Baixar Relatório de Correção" (navy)
- Botão inferior: "Tentar Novamente" (navy) com ícone ArrowLeft
- Nota de rodapé: italic 12px gray-400

### 5. Supplier History (Meus Envios)
- Cabeçalho da tabela com: botão Filter (ghost) + input de busca inline
- Tabela: ID | Arquivo | Período | Versão (badge) | Status (badge) | Data | Ação
- Ação "Cancelar" apenas para status valid; ChevronRight para os demais
- Linhas clicáveis → detalhe do envio

---

## 13. Telas Previstas — Perfil Admin

### 6. Admin Dashboard (Painel de Controle)
- 6 cards KPI com accent navy inferior: Esperados | Enviaram | Pendentes | Válidos | Com Erro | Cancelados
- Filtro de período (select) acima da tabela
- Tabela de status por fornecedor: Fornecedor | Período | Status | Último Envio | Versão | Erros | Ação
  - Hover: border-left navy
  - Ação: botão "Notificar" (amarelo) para pendentes; link "Ver Detalhe" para os demais
- Banner informativo MVP (amarelo): nota sobre notificações manuais

### 7. Admin Upload Detail (Auditoria de Envio)
- Botão "Voltar" com ícone ArrowLeft
- Grid: col-span-2 (detalhes) + col-span-1 (sumário lateral)
- Card principal:
  - Cabeçalho: ícone status + ID do upload + nome do arquivo + badge status
  - Grid de metadados: Fornecedor | Período | Versão | Enviado por | Data/Hora | Tabela Destino (font-mono blue)
- Card ciclo de vida: stepper horizontal com 4 etapas (Recebido → Validado → Normalizado → Publicado)
- Card sumário lateral (border-bottom amarelo): Linhas Totais | Válidas | Inválidas; botão "Reprocessar Lote" (outline navy, admin only)
- Card SQL de rastreabilidade: bloco navy escuro com código mono

### 8. Admin Suppliers (Gestão de Fornecedores)
- Tabela com todos os fornecedores cadastrados
- Filtros por período e status
- Ações por linha

### 9. Validated Data (Consulta Trusted)
- Painel de filtros: Fornecedor | Filial | Material | Período + botão Filtrar
- Tabela "Forecast Consolidado (Trusted)": Fornecedor | Filial | Cód. Mat. | Descrição | Período | Quant. | Ver. | Data Proc.
  - Hover: border-left blue-400
  - Corpo: font-mono italic 11px; exceção: Fornecedor em font-sans não-italic
- Botões de exportação: CSV e XLSX (ghost com ícone Download)
- Banner inferior: "Visão Analítica" + botão "Abrir Power BI" (amarelo)

---

## 14. Regras para Manter a Identidade Visual Komatsu

1. **Nunca usar outra cor de fundo** além de `#F4F5F7` para o body e `#FFFFFF` para cards/painéis.
2. **Nunca usar amarelo como fundo de texto longo** — apenas para botões, logos e destaques pontuais.
3. **O texto sobre amarelo é sempre navy.** O texto sobre navy é sempre branco.
4. **Fontes:** Inter para todo o corpo. Outfit exclusivamente para o logo "KOMATSU". Monospace para dados técnicos.
5. **Border-radius de cards:** sempre `12px`. Nunca usar cantos muito arredondados (ex: `9999px`) em containers grandes.
6. **Ícones:** usar somente da biblioteca Lucide (equivalentes Python: `streamlit-lucide` se disponível, ou Unicode/SVG embutido).
7. **Labels de campo:** sempre `10px`, `uppercase`, `bold`, `gray-400`, com `letter-spacing` amplo. Nunca em caixa normal.
8. **Sombras:** apenas `shadow-sm` (`0 1px 3px rgba(0,0,0,0.05)`). Sem sombras profundas em cards.
9. **Separação visual entre seções:** usar `margin-top: 24px` e `border-top` suave. Nunca usar linhas grossas ou divisores coloridos.
10. **Mensagens de estado:** sempre usar banners com ícone + título + texto. Nunca mensagens soltas sem container.
11. **Tabelas:** nunca usar `st.table` padrão sem override de CSS. O estilo padrão do Streamlit não é compatível.
12. **Botões destrutivos** (cancelar, excluir): nunca usar o mesmo estilo de um CTA primário. Sempre com aparência mais discreta.

---

## 15. Componentes Streamlit a Criar

| Arquivo | Responsabilidade |
|---|---|
| `app/assets/style.css` | CSS global: variáveis, resets Streamlit, todas as classes documentadas acima |
| `app/components/layout.py` | `render_page(title)`: injeta CSS, renderiza header HTML customizado e rodapé |
| `app/components/navigation.py` | `render_sidebar(role, current_page)`: monta sidebar com logo, menu por perfil, widget janela, logout |
| `app/components/cards.py` | `metric_card(label, value, detail)` / `action_card(icon, label)` / `navy_card(title, text)` |
| `app/components/badges.py` | `status_badge(status)` → string HTML / `version_badge(n)` → string HTML |
| `app/components/tables.py` | `styled_table(df, accent)` → HTML table com hover, badges, colunas especiais |
| `app/components/alerts.py` | `error_alert(title, msg)` / `success_alert(title, msg)` / `info_banner(msg)` → HTML |

### Regras de implementação CSS no Streamlit

- Todo CSS é injetado via `st.markdown('<style>...</style>', unsafe_allow_html=True)` em `layout.py`.
- O arquivo `style.css` é lido pelo `layout.py` e injetado uma única vez por sessão.
- Componentes que usam HTML devem retornar string e ser renderizados via `st.markdown(..., unsafe_allow_html=True)`.
- Overrides do Streamlit (ex: `.stButton > button`) devem estar em `style.css`, não inline.
- Nunca usar `st.write` para renderizar HTML — sempre `st.markdown`.
- Para Streamlit in Snowflake: não usar `st.set_page_config` com parâmetros incompatíveis. Testar `layout="wide"` e `initial_sidebar_state="expanded"`.
