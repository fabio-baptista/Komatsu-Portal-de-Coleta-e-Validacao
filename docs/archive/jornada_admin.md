# Jornada do Administrador — Portal de Coleta e Validação de Forecast

## 1. Visão Geral

O perfil **admin** é responsável por acompanhar o ciclo de coleta de forecast enviado pelos fornecedores/distribuidores. O admin não envia arquivos nem cancela envios — ele monitora, gerencia fornecedores e consulta dados consolidados.

### O que o admin consegue acompanhar

- Participação dos fornecedores no período de coleta.
- Status de entrega de cada fornecedor (válido, pendente, cancelado).
- Detalhe de cada envio específico (linhas, erros, versão, timestamps).
- Dados finais validados prontos para consumo analítico.
- Cadastro e status de fornecedores.

### Fontes de dados (Snowflake)

| Tabela | Uso |
|--------|-----|
| `CONTROL.USERS` | Autenticação do admin |
| `CONTROL.SUPPLIERS` | Cadastro de fornecedores |
| `CONTROL.UPLOAD_BATCHES` | Histórico de uploads, status, versionamento |
| `CONTROL.VALIDATION_ERRORS` | Erros de validação por upload |
| `CONTROL.SUBMISSION_WINDOWS` | Janela de envio aberta (período atual) |
| `TRUSTED.FORECAST_VALIDATED` | Dados finais dos forecasts válidos e ativos |

---

## 2. Login do Admin

### Como acessar

O admin acessa pela tela de login selecionando o perfil "Administrativo" e informando e-mail e senha.

### Fluxo técnico

1. Função: `do_admin_login(email, password)` em `services/auth_service.py`.
2. Tabela: `KBI_DATA_JOURNEY_DEV_DB.CONTROL.USERS`.
3. Hash de senha: `SHA2("salt_kmt_" || password || "_portal", 256)` — executado no Snowflake.
4. Condições: `ROLE = 'admin'` e `IS_ACTIVE = TRUE`.
5. Modo passwordless: se senha vazia, busca apenas por e-mail + role + is_active (para SSO futuro).

### Após login bem-sucedido

- `session_state.role` = `"admin"`
- `session_state.page` = `"admin_dashboard"`
- `session_state.user_name`, `user_email`, `user_initials` preenchidos.

---

## 3. Painel Administrativo (Home do Admin)

**Tela:** `admin_dashboard.py`
**Rota:** `page = "admin_dashboard"`

### Cards KPI (4)

| Card | Cálculo |
|------|---------|
| **Participantes** | Fornecedores ativos (`CONTROL.SUPPLIERS WHERE STATUS='active'`) |
| **Enviaram Forecast Válido** | Fornecedores com upload `STATUS='VALID'` e `IS_ACTIVE=TRUE` no período |
| **Pendentes** | Participantes - Válidos (inclui inválidos e cancelados sem reenvio) |
| **Envios Cancelados** | `COUNT(DISTINCT UPLOAD_ID) WHERE STATUS='CANCELLED' AND REFERENCE_PERIOD=?` |

### Filtros

| Filtro | Tipo | Fonte |
|--------|------|-------|
| Período | Selectbox | `DISTINCT REFERENCE_PERIOD` de `CONTROL.UPLOAD_BATCHES` + janela aberta |
| Fornecedor | Multiselect | Nomes dos fornecedores ativos (`CONTROL.SUPPLIERS`) |
| Status | Multiselect | Válido, Inválido, Pendente, Cancelado, Substituído |

### Tabela "Status por Fornecedor"

| Coluna | Descrição |
|--------|-----------|
| Fornecedor | Nome do fornecedor |
| Código | Código identificador (ex: SUP006) |
| Período | Período filtrado |
| Status da Coleta | Badge: valid/pending/invalid/canceled/replaced |
| Último Envio | Data/hora do upload mais recente no período |
| Versão Ativa | Versão do upload VALID ativo, ou "—" |
| Erros | Contagem de INVALID_ROWS, ou "—" |

### Ações por fornecedor

- **Ver detalhe** — para uploads com status valid ou replaced.
- **Ver erros** — para uploads com status invalid.

### Navegação rápida

- "Gestão de Fornecedores" → tela `admin_suppliers`
- "Forecasts Recebidos" → tela `validated_data` (menu lateral: "Forecasts Validados")

### Query principal (CTE)

```sql
WITH latest_uploads AS (
    SELECT SUPPLIER_ID, UPLOAD_ID, STATUS, IS_ACTIVE, VERSION, INVALID_ROWS, UPLOADED_AT,
           ROW_NUMBER() OVER (PARTITION BY SUPPLIER_ID ORDER BY ...) AS RN
    FROM CONTROL.UPLOAD_BATCHES WHERE REFERENCE_PERIOD = ?
)
SELECT s.SUPPLIER_NAME, s.SUPPLIER_CODE, lu.*
FROM CONTROL.SUPPLIERS s
LEFT JOIN latest_uploads lu ON s.SUPPLIER_CODE = lu.SUPPLIER_ID AND lu.RN = 1
WHERE s.STATUS = 'active'
```

---

## 4. Gestão de Fornecedores

**Tela:** `admin_suppliers.py`
**Rota:** `page = "admin_suppliers"`

### Cadastro de fornecedor

| Campo | Obrigatório | Detalhes |
|-------|-------------|----------|
| Nome | Sim | Texto livre |
| E-mail | Sim | Validado para formato + unicidade; usado como login do fornecedor |
| Status | Sim | Ativo ou Inativo (padrão: Ativo) |
| Código | Auto-gerado | Sequencial via `get_next_supplier_code()` (ex: SUP009) |

### Geração do código

Função `get_next_supplier_code()` em `supplier_service.py`:
- Busca o maior `SUPPLIER_CODE` no formato `SUPnnn` em `CONTROL.SUPPLIERS`.
- Incrementa em 1.
- Retorna `SUP{next_number:03d}`.

### Ativação/Inativação

- **Fornecedor ativo**: participa da coleta, aparece como "Participante" no painel, pode fazer login.
- **Fornecedor inativo**: não aparece no painel de coleta, não conta como pendente, não consegue fazer login.
- Toggle via botões "Inativar" / "Ativar" na tabela de fornecedores.

### Relação com login

- O e-mail cadastrado é o identificador de login do fornecedor.
- Fornecedor inativo no `CONTROL.SUPPLIERS` não consegue autenticar (bloqueado em `auth_service`).

### Tabela Snowflake

```
CONTROL.SUPPLIERS (
    SUPPLIER_ID, SUPPLIER_CODE, SUPPLIER_NAME, EMAIL, STATUS, CREATED_AT, UPDATED_AT
)
```

---

## 5. Acompanhamento de Envios

### Regras de status

| Status | Significado | IS_ACTIVE | VERSION |
|--------|-------------|-----------|---------|
| `VALID` | Arquivo aprovado; linhas disponíveis para consumo | `TRUE` | Sequencial (1, 2, 3...) |
| `INVALID` | Arquivo com erros de validação | `FALSE` | `0` (sentinela — não consome numeração) |
| `REPLACED` | Upload válido anterior substituído por versão mais recente | `FALSE` | Original mantido |
| `CANCELLED` | Upload válido cancelado pelo fornecedor | `FALSE` | Original mantido |

### Como o admin identifica cada situação

| Situação | Indicador no painel |
|----------|---------------------|
| Fornecedor enviou forecast válido | Status = "Válido", versão ativa exibida |
| Fornecedor pendente | Status = "Pendente", sem versão ativa |
| Fornecedor com envio inválido | Status = "Pendente" no painel (inválido = pendente para o admin) |
| Envio cancelado | Card "Envios Cancelados" incrementa; fornecedor volta a Pendente se não reenviar |
| Versão substituída | Uploads anteriores ficam como REPLACED; apenas o mais recente VALID aparece |

### Versionamento funcional

- Chave: `SUPPLIER_ID | REPORT_TYPE | REFERENCE_PERIOD`
- Cada novo upload VALID incrementa a versão.
- Uploads INVALID recebem VERSION=0 (não consomem numeração).
- Novo upload VALID marca o anterior como REPLACED (IS_ACTIVE=FALSE).

---

## 6. Detalhe do Envio

**Tela:** `admin_upload_detail.py`
**Rota:** `page = "admin_upload_detail"`

### Informações exibidas

| Campo | Fonte |
|-------|-------|
| Upload ID | `CONTROL.UPLOAD_BATCHES.UPLOAD_ID` |
| Fornecedor | `SUPPLIER_NAME` |
| Arquivo | `FILE_NAME` |
| Tipo de Relatório | `REPORT_TYPE` |
| Período | `REFERENCE_PERIOD` |
| Versão | `VERSION` |
| Status | `STATUS` (com badge visual) |
| Enviado por | `UPLOADED_BY` |
| Data de Envio | `UPLOADED_AT` |
| Total de Linhas | `TOTAL_ROWS` |
| Linhas Válidas | `VALID_ROWS` |
| Linhas com Erro | `INVALID_ROWS` |

### Cards de resumo

- Total de Linhas
- Linhas Válidas
- Linhas com Erro
- Status do Processamento (Processado / Com Erros / Cancelado / Substituído)

### Ações disponíveis

| Ação | Quem pode | Condição |
|------|-----------|----------|
| Voltar | Admin e Fornecedor | Sempre |
| Baixar relatório | Admin e Fornecedor | Sempre |
| Cancelar envio | **Somente Fornecedor** | `can_cancel()` = True |

> **Regra MVP:** O admin **não pode** cancelar envios. Ele apenas acompanha o status. O cancelamento é ação exclusiva do fornecedor dentro da janela aberta.

### Fonte de dados

Função `get_upload_detail(upload_id)` em `upload_service.py`:
1. Consulta `CONTROL.UPLOAD_BATCHES` no Snowflake (fonte principal).
2. Fallback: session_state → mock (apenas em caso de falha).

---

## 7. Consulta de Forecasts Validados

**Tela:** `validated_data.py`
**Rota:** `page = "validated_data"`
**Menu lateral:** "Forecasts Validados"
**Botão no painel:** "Forecasts Recebidos"

### Fonte de verdade

```sql
SELECT * FROM TRUSTED.FORECAST_VALIDATED WHERE IS_ACTIVE = TRUE ORDER BY UPLOADED_AT DESC
```

### Filtros disponíveis (4)

| Filtro | Tipo | Comportamento |
|--------|------|---------------|
| Período | Selectbox | Default: janela aberta ou "Todos os períodos" |
| Fornecedor | Selectbox | "Todos os fornecedores" ou nome específico |
| Filial | Selectbox | "Todas as filiais" ou filial específica |
| Material | Selectbox | "Todos os materiais" ou código específico |

### Cards de resumo (4-5)

| Card | Cálculo |
|------|---------|
| Registros Validados | count de linhas após filtro |
| Fornecedores | count distinct de suppliers |
| Período | label do período selecionado |
| Qtd. Prevista Total | sum(forecast_quantity) |
| Versão Ativa | max(version) — só quando fornecedor E período específicos |

### Tabela

| Coluna | Campo Snowflake |
|--------|-----------------|
| Fornecedor | SUPPLIER_NAME |
| Filial | BRANCH |
| Cód. Material | MATERIAL_CODE |
| Descrição | MATERIAL_DESCRIPTION |
| Período | FORECAST_PERIOD (formatado "Maio/2026") |
| Qtd. | FORECAST_QUANTITY |
| Versão | UPLOAD_VERSION |
| Data de Envio | UPLOADED_AT |
| Arquivo | SOURCE_FILE_NAME |

### Exportação

- **XLSX** — via openpyxl (colunas renomeadas para PT-BR).
- **CSV** — sempre disponível.
- Ambos exportam os dados filtrados (não a tabela completa).

---

## 8. Rastreabilidade e Governança

### Campos de auditoria

| Campo | Tabela | Descrição |
|-------|--------|-----------|
| `UPLOAD_ID` | UPLOAD_BATCHES | UUID v4, identificador único do envio |
| `SUPPLIER_ID` | UPLOAD_BATCHES | Código do fornecedor (vem do login, nunca da planilha) |
| `UPLOADED_BY` | UPLOAD_BATCHES | E-mail do fornecedor que fez o upload |
| `UPLOADED_AT` | UPLOAD_BATCHES | Timestamp do recebimento |
| `VERSION` | UPLOAD_BATCHES | Versão sequencial por chave funcional |
| `VERSION_KEY` | UPLOAD_BATCHES | Chave composta: `supplier_id|report_type|reference_period` |
| `STATUS` | UPLOAD_BATCHES | VALID, INVALID, REPLACED, CANCELLED |
| `IS_ACTIVE` | UPLOAD_BATCHES | TRUE apenas para o upload vigente |
| `CANCELLED_AT` | UPLOAD_BATCHES | Timestamp do cancelamento |
| `CANCELLED_BY` | UPLOAD_BATCHES | E-mail de quem cancelou |
| `CANCELLATION_REASON` | UPLOAD_BATCHES | Motivo (texto livre) |
| `ERROR_ID` | VALIDATION_ERRORS | UUID por erro |
| `ROW_NUMBER` | VALIDATION_ERRORS | Linha do arquivo onde o erro ocorreu |
| `ROW_ID` | FORECAST_VALIDATED | UUID por linha validada |
| `IS_ACTIVE` | FORECAST_VALIDATED | TRUE para linhas do upload ativo |

### Logs técnicos

O app utiliza logging centralizado (`utils/logger.py`) com nível INFO/WARNING/ERROR:
- Início e fim de cada operação de persistência.
- Quantidade de registros inseridos/consultados.
- Falhas com tipo de exceção e mensagem.
- Fallback para session_state quando Snowflake não retorna dados.

---

## 9. Regras Importantes

1. **Fornecedor oficial vem do login**, nunca do conteúdo da planilha.
2. **Upload inválido não entra na TRUSTED** — apenas CONTROL.UPLOAD_BATCHES e CONTROL.VALIDATION_ERRORS.
3. **Upload inválido usa VERSION=0** — sentinela que não consome numeração.
4. **Upload válido consome versão real** — incrementada sobre MAX(VERSION) da mesma VERSION_KEY.
5. **Upload substituído fica REPLACED** — quando um novo upload VALID chega para a mesma chave.
6. **Upload cancelado fica CANCELLED** — IS_ACTIVE=FALSE, CANCELLED_AT/BY preenchidos.
7. **Forecasts Validados mostram apenas IS_ACTIVE=TRUE** — uploads substituídos/cancelados não aparecem.
8. **Admin não cancela envios** — apenas monitora. Cancelamento é ação do fornecedor.
9. **Janela de envio** — cancelamento só é permitido dentro da janela aberta (`CONTROL.SUBMISSION_WINDOWS`).

---

## 10. Teste Ponta a Ponta — Roteiro

### Preparação

1. Garantir que existe pelo menos uma janela aberta em `CONTROL.SUBMISSION_WINDOWS`.
2. Garantir que `CONTROL.USERS` tem um registro admin ativo.

### Execução

| Passo | Ação | Validação |
|-------|------|-----------|
| 1 | Entrar como admin | Painel administrativo abre |
| 2 | Ir para Gestão de Fornecedores | Lista de fornecedores aparece |
| 3 | Cadastrar fornecedor (Nome, E-mail) | Código gerado automaticamente; aparece na lista |
| 4 | Inativar o fornecedor | Status muda para "Inativo"; some do card "Participantes" |
| 5 | Reativar o fornecedor | Status muda para "Ativo"; volta para "Participantes" |
| 6 | Sair e entrar como o fornecedor cadastrado | Login funciona; home do fornecedor abre |
| 7 | Enviar arquivo válido | Upload registrado; TRUSTED recebe linhas; VERSION incrementa |
| 8 | Sair e entrar como admin | Painel mostra fornecedor como "Válido" |
| 9 | Clicar "Ver detalhe" do fornecedor | Tela de detalhe abre com dados do Snowflake |
| 10 | Sair e entrar como fornecedor | Enviar arquivo inválido |
| 11 | Sair e entrar como admin | Painel mostra fornecedor como "Pendente" (inválido = pendente) |
| 12 | Clicar "Ver erros" | Tela de erros abre com dados de VALIDATION_ERRORS |
| 13 | Entrar como fornecedor e cancelar envio válido | UPLOAD_BATCHES: STATUS=CANCELLED, IS_ACTIVE=FALSE |
| 14 | Entrar como admin | Card "Envios Cancelados" incrementa; fornecedor volta a Pendente |
| 15 | Ir para "Forecasts Validados" | Dados do upload cancelado NÃO aparecem (IS_ACTIVE=FALSE) |
| 16 | Verificar Snowflake | Queries abaixo confirmam estado |

### Queries de verificação

```sql
-- Uploads do fornecedor no período
SELECT UPLOAD_ID, STATUS, IS_ACTIVE, VERSION
FROM CONTROL.UPLOAD_BATCHES
WHERE SUPPLIER_ID = 'SUPxxx' AND REFERENCE_PERIOD = '2026-05';

-- Erros de um upload inválido
SELECT COUNT(*) FROM CONTROL.VALIDATION_ERRORS WHERE UPLOAD_ID = '<id>';

-- Forecasts ativos (apenas uploads VALID com IS_ACTIVE=TRUE)
SELECT COUNT(*) FROM TRUSTED.FORECAST_VALIDATED WHERE IS_ACTIVE = TRUE;

-- Upload cancelado
SELECT STATUS, IS_ACTIVE, CANCELLED_AT, CANCELLED_BY
FROM CONTROL.UPLOAD_BATCHES WHERE UPLOAD_ID = '<id>';
```

---

## 11. Limitações Atuais

| Limitação | Detalhes |
|-----------|----------|
| `RAW.UPLOADED_FILE_ROWS` | DDL existe, mas o app não grava o arquivo bruto nesta tabela |
| `STAGING.FORECAST_NORMALIZED` | DDL existe, mas o app grava direto na TRUSTED (sem staging intermediário) |
| Report type fixo | App é específico para "Forecast DB" — vendas, vendas perdidas e estoque são evolução futura |
| Fallbacks de session_state | Existem como compatibilidade/dev; Snowflake é fonte principal |
| Paginação | Tabelas limitadas a 50 linhas sem paginação real |
| Autenticação | SHA2 simples; sem integração com SSO corporativo |
| Template único | Apenas `template_forecast.xlsx/csv` disponível |
| Admin não cancela | Decisão de MVP; admin apenas monitora |

---

## 12. Evoluções Futuras

| Evolução | Descrição |
|----------|-----------|
| Multi-report | Suporte a vendas, vendas perdidas, estoque (registry de validação/template por tipo) |
| RAW layer | Gravar arquivo bruto em RAW.UPLOADED_FILE_ROWS para auditoria completa |
| STAGING layer | Etapa intermediária de normalização antes da TRUSTED |
| SSO corporativo | Integração com Azure AD / Okta para login |
| Paginação real | Tabelas com mais de 50 registros |
| Notificações | Alertas por e-mail quando fornecedor está pendente |
| Janela automática | Abertura/fechamento automático de janelas via cron |
| API REST | Endpoints para integração com sistemas corporativos |
| Dashboard analítico | Gráficos de tendência, comparação entre períodos |
| Cancelamento admin | Permitir admin cancelar em cenários específicos (evolução futura) |
