# Jornada do Fornecedor — Portal de Coleta e Validação de Forecast

## 1. Objetivo da Jornada

A jornada do fornecedor tem como objetivo permitir que distribuidores/fornecedores enviem arquivos de forecast de forma padronizada, validada e rastreável, substituindo o envio manual por e-mail por um fluxo operacional dentro do portal.

O fornecedor deve conseguir:

- baixar o template oficial;
- preencher a planilha localmente;
- enviar o arquivo no portal;
- receber validação automática;
- corrigir erros quando necessário;
- reenviar arquivos corrigidos;
- acompanhar histórico, versões e status dos próprios envios;
- cancelar envios permitidos dentro da janela configurada.

---

## 2. Perfil do Usuário Fornecedor

O fornecedor é um usuário com acesso restrito ao próprio contexto.

Ele pode visualizar apenas:

- seus próprios envios;
- seus próprios erros de validação;
- seu histórico de versões;
- seus arquivos válidos, inválidos ou cancelados.

Ele não deve visualizar:

- dados de outros fornecedores;
- painel administrativo;
- gestão de fornecedores;
- configurações internas;
- termos técnicos de infraestrutura.

---

## 3. Visão Geral do Fluxo

```
Acessar o portal
↓
Entrar como fornecedor (e-mail cadastrado)
↓
Visualizar dashboard inicial
↓
Baixar template oficial
↓
Preencher planilha fora do app
↓
Enviar arquivo .xlsx ou .csv
↓
Validar arquivo
↓
Se válido: envio registrado e disponível em Meus Envios
↓
Se inválido: visualizar erros, baixar relatório de correção e reenviar
↓
Acompanhar histórico, versões, detalhes e cancelamentos
```

---

## 4. Etapa 1 — Acesso ao Portal

O fornecedor acessa o portal por meio da tela inicial do aplicativo.

O login é feito com o **e-mail cadastrado pelo administrador** na Gestão de Fornecedores. O fornecedor precisa estar com status ativo para conseguir acessar.

### Resultado esperado

Após acessar como fornecedor, o usuário é direcionado para a área do fornecedor e visualiza apenas as telas permitidas para seu perfil:

- Dashboard (home)
- Enviar Arquivo
- Meus Envios

---

## 5. Etapa 2 — Dashboard do Fornecedor

O dashboard é a tela inicial da jornada do fornecedor.

Ele apresenta uma visão simples e operacional dos envios registrados.

### A tela contém

- Saudação ao fornecedor;
- Cards de acompanhamento:
  - **Último Envio** — data/hora do envio mais recente;
  - **Status Atual** — Válido/Ativo, Inválido, Substituído ou Cancelado;
  - **Versão Ativa** — versão do envio válido ativo (ex: v.4), ou "—" se não houver;
  - **Linhas Processadas** — total de linhas do último envio (com indicador de erros se houver).
- Atalhos para:
  - Enviar arquivo;
  - Ir para templates e envio;
  - Consultar Meus Envios.

### Dados persistentes

O dashboard mostra dados dos envios registrados, mesmo após recarregar a página ou sair e entrar novamente. O histórico é persistente.

### Estado inicial (sem envios)

Quando o fornecedor ainda não realizou nenhum envio:

- Último envio: Sem envio
- Status atual: Pendente
- Versão ativa: —
- Linhas processadas: 0

### O que não aparece no dashboard

- Tabela completa de rastreabilidade (pertence a Meus Envios);
- Erros detalhados (pertence à tela de erros);
- Informações técnicas internas.

---

## 6. Etapa 3 — Download do Template Oficial

O fornecedor acessa a tela de envio e baixa o template oficial.

O portal disponibiliza dois modelos:

- template .xlsx;
- template .csv.

Ambos contêm as mesmas colunas oficiais:

| Coluna | Descrição |
|--------|-----------|
| Data_Envio | Data de envio do forecast |
| Distribuidor_Nome | Nome do distribuidor/fornecedor |
| Cidade_Filial | Filial ou localidade |
| NFMAT | Código NF do material |
| MATERIAL | Código do material |
| Descrição | Descrição do material |
| Ranking_Nacional | Ranking (informativo) |
| Qtd | Quantidade prevista |
| Data_recebimento | Data de recebimento/período |
| Observacoes | Observações (opcional) |

### Regra importante

O template oficial está disponível na tela de envio. O fornecedor baixa, preenche localmente e retorna ao portal para enviar.

---

## 7. Etapa 4 — Envio do Arquivo de Forecast

A tela "Enviar Arquivo" concentra:

- download dos templates oficiais;
- orientação sobre colunas esperadas;
- seleção do arquivo;
- botão de validação;
- retorno de sucesso ou erro.

O fornecedor pode enviar arquivos `.xlsx` ou `.csv`.

O arquivo **não é processado automaticamente** ao ser selecionado. O fornecedor deve clicar no botão **"Validar arquivo"** para iniciar a validação.

---

## 8. Etapa 5 — Validação do Arquivo

O portal valida automaticamente a estrutura e o conteúdo do arquivo.

### Validações realizadas

1. Extensão do arquivo (.xlsx ou .csv);
2. Arquivo vazio;
3. Colunas obrigatórias presentes (aceita aliases);
4. Linhas totalmente vazias (removidas);
5. Material obrigatório;
6. Filial/localidade obrigatória;
7. Quantidade obrigatória;
8. Quantidade numérica;
9. Quantidade maior ou igual a zero;
10. Data válida (múltiplos formatos aceitos);
11. Compatibilidade do fornecedor da planilha com o fornecedor logado (quando a coluna existe).

### Se o arquivo for válido

O fornecedor recebe mensagem:

> Arquivo válido para processamento. Todas as validações foram aprovadas. O envio foi registrado e está disponível em Meus Envios.

O envio é registrado com uma nova versão e fica disponível imediatamente.

### Se o arquivo for inválido

O fornecedor recebe mensagem:

> Arquivo inválido. Corrija os erros na planilha original e realize um novo envio.

O envio inválido é registrado no histórico mas **não substitui** a versão válida ativa (se existir).

---

## 9. Etapa 6 — Correção de Erros

Quando o arquivo contém inconsistências, o portal apresenta os erros encontrados.

Cada erro contém:

| Campo | Descrição |
|-------|-----------|
| Linha | Número da linha no arquivo |
| Coluna | Nome da coluna com problema |
| Valor informado | O que foi encontrado na célula |
| Erro | Tipo do problema detectado |
| Orientação | Como corrigir |

### Exemplo

| Linha | Coluna | Valor informado | Erro | Orientação |
|-------|--------|-----------------|------|-----------|
| 15 | MATERIAL | (vazio) | Campo obrigatório | Informar código do material |
| 22 | Qtd | ABC | Tipo inválido | Informar valor numérico |
| 31 | Data_recebimento | 32/13/2026 | Data inválida | Informar data válida (DD/MM/AAAA) |

### Relatório de correção

O fornecedor pode **baixar o relatório de correção** em formato XLSX ou CSV. Este relatório contém todos os erros encontrados e pode ser usado como guia para correção da planilha.

O app **não altera o arquivo original**. O fornecedor corrige a planilha localmente e faz um novo envio.

### Persistência dos erros

Os erros ficam registrados e disponíveis para consulta mesmo após recarregar a página. O fornecedor pode acessar "Meus Envios" e clicar em "Ver erros" a qualquer momento para consultar os problemas de um envio inválido.

---

## 10. Etapa 7 — Meus Envios

A tela "Meus Envios" concentra o histórico operacional do fornecedor.

### Informações exibidas

| Campo | Descrição |
|-------|-----------|
| Upload ID | Identificador único do envio |
| Arquivo | Nome do arquivo enviado |
| Período | Período de referência do forecast |
| Versão | Número da versão (ou 0 para inválidos) |
| Status | Situação do arquivo |
| Data de envio | Quando o arquivo foi enviado |
| Linhas válidas | Linhas aceitas |
| Linhas com erro | Linhas rejeitadas |

### Cards de resumo

- Total de Envios
- Versão Ativa (maior versão válida)
- Arquivos Válidos
- Com Erro

### Status possíveis

- **Válido/Ativo** — envio aceito e vigente;
- **Inválido** — envio com erros (permite "Ver erros");
- **Substituído** — versão anterior substituída por envio mais recente;
- **Cancelado** — envio cancelado pelo fornecedor.

### Ações disponíveis

- **Ver erros** — para envios inválidos (abre tela de erros);
- **Ver detalhe** — para envios válidos, substituídos ou cancelados;
- **Cancelar envio** — para o envio válido ativo dentro da janela permitida.

### Persistência

O histórico é persistente: sobrevive a refresh da página, saída e reentrada no portal. Todos os envios (válidos, inválidos, substituídos e cancelados) permanecem no histórico para rastreabilidade.

---

## 11. Etapa 8 — Versionamento

Cada novo envio válido cria uma nova versão.

### Chave de versionamento

Fornecedor + tipo de relatório + período

### Regras

| Cenário | Resultado |
|---------|-----------|
| Novo envio válido para o mesmo período | Nova versão criada; versão anterior fica como "Substituído" |
| Envio inválido | Registrado com versão 0; não substitui a versão válida ativa |
| Cancelamento de versão ativa | Versão fica como "Cancelado"; fornecedor pode reenviar para criar nova versão |

### O que o fornecedor vê

- A versão ativa é sempre a mais recente válida.
- Versões substituídas permanecem no histórico com status "Substituído".
- O fornecedor vê o número da versão em cada linha do histórico.

---

## 12. Etapa 9 — Detalhe do Envio

A tela de detalhe permite ao fornecedor consultar informações de um envio específico.

### Informações exibidas

- Upload ID;
- Fornecedor;
- Arquivo;
- Período;
- Versão;
- Status;
- Quem enviou;
- Data de envio;
- Total de linhas;
- Linhas válidas;
- Linhas com erro.

### O que não aparece para o fornecedor

A tela do fornecedor não exibe termos técnicos como nomes de tabelas, camadas de dados ou identificadores internos de infraestrutura.

---

## 13. Etapa 10 — Cancelamento Lógico

O fornecedor pode cancelar um envio quando a regra permitir.

### Condições para cancelamento

O botão "Cancelar envio" aparece apenas quando o envio:

- é válido;
- é a versão ativa;
- está dentro da janela de envio permitida.

**Não é possível cancelar:**

- envios inválidos;
- envios já cancelados;
- envios substituídos;
- envios fora da janela permitida.

### O que acontece ao cancelar

O cancelamento é **lógico**:

- O registro **não é excluído**.
- O status muda para "Cancelado".
- O envio deixa de ser a versão ativa.
- O histórico é preservado.
- O fornecedor pode visualizar o envio cancelado em Meus Envios.
- O dados do forecast cancelado não aparecem mais na tela Forecasts Validados.

Mensagem esperada:

> Envio cancelado com sucesso. O registro foi mantido no histórico com status Cancelado.

---

## 14. Regras Importantes

### 14.1. O fornecedor oficial vem do login

Mesmo que a planilha contenha nome do fornecedor, o fornecedor oficial é identificado pelo usuário autenticado. A planilha pode ser usada apenas para conferência.

### 14.2. O fornecedor vê apenas seus próprios dados

O fornecedor não acessa envios de outros fornecedores, dados consolidados, telas administrativas ou cadastro de fornecedores.

### 14.3. O app não é uma ferramenta de edição

O fluxo correto é:

```
Baixar template → Preencher/corrigir localmente → Enviar novamente
```

O fornecedor não edita dados diretamente no portal.

### 14.4. Linguagem operacional

A jornada do fornecedor usa linguagem simples e direta. Termos adequados:

- Arquivo válido / Arquivo inválido
- Corrigir planilha
- Baixar relatório de correção
- Ver meus envios / Ver detalhe
- Cancelar envio

---

## 15. Resultado Esperado da Jornada

Ao final da jornada, o fornecedor deve conseguir:

- acessar o portal com seu e-mail cadastrado;
- baixar o template oficial;
- preencher a planilha localmente;
- enviar arquivo .xlsx ou .csv;
- receber validação automática;
- corrigir erros quando houver;
- baixar relatório de correção;
- reenviar arquivo corrigido;
- acompanhar histórico e versões (persistente entre sessões);
- visualizar detalhes do envio;
- cancelar envio quando permitido;
- ter segurança de que visualiza apenas os próprios dados.

---

## 16. Critério de Aceite

A jornada pode ser considerada pronta quando os seguintes fluxos forem executados sem erro:

1. Entrar como fornecedor (e-mail cadastrado pelo admin).
2. Visualizar dashboard inicial com dados persistentes.
3. Baixar template XLSX.
4. Baixar template CSV.
5. Enviar arquivo válido.
6. Ver envio válido em Meus Envios com versão incrementada.
7. Enviar arquivo inválido.
8. Confirmar que envio inválido usa versão 0 e não substitui a versão ativa.
9. Ver erros do envio inválido.
10. Baixar relatório de correção.
11. Reenviar arquivo corrigido.
12. Confirmar nova versão ativa; versão anterior como "Substituído".
13. Cancelar envio válido ativo dentro da janela.
14. Confirmar envio cancelado no histórico (status "Cancelado").
15. Confirmar que fornecedor não vê telas administrativas.
16. Recarregar a página e confirmar que o histórico permanece.

---

## 17. Evoluções Futuras

| Item | Descrição |
|------|-----------|
| Coleta de Vendas | Envio de relatórios de vendas (tipo de relatório diferente) |
| Coleta de Vendas Perdidas | Relatório de oportunidades perdidas |
| Coleta de Estoque | Posição de estoque do distribuidor |
| Notificações | Alertas por e-mail sobre prazos e pendências |
| SSO corporativo | Login integrado ao ambiente do cliente |

---

## Jornada Resumida

```
Fornecedor acessa o portal
↓
Faz login com e-mail cadastrado
↓
Consulta seu dashboard (dados persistentes)
↓
Baixa o template oficial
↓
Preenche o arquivo fora do app
↓
Envia o forecast
↓
App valida automaticamente
↓
Se houver erro: fornecedor baixa relatório e corrige
↓
Se estiver válido: envio registrado com nova versão
↓
Fornecedor acompanha versões, status e detalhes
↓
Fornecedor pode cancelar envio ativo dentro da janela
```
