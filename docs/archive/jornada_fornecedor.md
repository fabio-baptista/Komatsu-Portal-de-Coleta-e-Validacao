Jornada do Fornecedor — Portal de Coleta e Validação de Forecast
1. Objetivo da Jornada

A jornada do fornecedor tem como objetivo permitir que distribuidores/fornecedores enviem arquivos de forecast de forma padronizada, validada e rastreável, substituindo o envio manual por e-mail por um fluxo operacional dentro do portal.

O fornecedor deve conseguir:

baixar o template oficial;
preencher a planilha localmente;
enviar o arquivo no portal;
receber validação automática;
corrigir erros quando necessário;
reenviar arquivos corrigidos;
acompanhar histórico, versões e status dos próprios envios;
cancelar envios permitidos dentro da janela configurada.
2. Perfil do Usuário Fornecedor

O fornecedor é um usuário com acesso restrito ao próprio contexto.

Ele pode visualizar apenas:

seus próprios envios;
seus próprios erros de validação;
seu histórico de versões;
seus arquivos válidos, inválidos ou cancelados.

Ele não deve visualizar:

dados de outros fornecedores;
painel administrativo;
gestão de fornecedores;
configurações internas;
termos técnicos de infraestrutura, como Snowflake, RAW, STAGING ou TRUSTED.
3. Visão Geral do Fluxo

A jornada do fornecedor segue o fluxo abaixo:

Acessar o portal
↓
Entrar como fornecedor
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
4. Etapa 1 — Acesso ao Portal

O fornecedor acessa o portal por meio da tela inicial do aplicativo.

No MVP local, o acesso é simulado por perfil. Em uma versão futura, o login deverá ser integrado ao mecanismo de autenticação definido para o ambiente do cliente.

Resultado esperado

Após acessar como fornecedor, o usuário é direcionado para a área do fornecedor e visualiza apenas as telas permitidas para seu perfil.

5. Etapa 2 — Dashboard do Fornecedor

O dashboard é a tela inicial da jornada do fornecedor.

Ele deve apresentar uma visão simples e operacional, sem histórico detalhado.

A tela deve conter
saudação ao fornecedor;
resumo do último status;
indicação se há ou não forecast enviado;
cards simples de acompanhamento;
atalhos para:
enviar arquivo;
baixar template;
consultar meus envios.
Estado inicial esperado

Quando o fornecedor acessa pela primeira vez e ainda não realizou envios na sessão, o dashboard deve mostrar estado vazio, por exemplo:

Último envio: Sem envio
Status atual: Pendente
Versão ativa: -
Linhas processadas: 0
O que não deve aparecer no dashboard
tabela completa de rastreabilidade;
lista detalhada de arquivos;
erros detalhados;
dados normalizados;
informações técnicas internas.

Essas informações pertencem à tela Meus Envios ou à tela de erros.

6. Etapa 3 — Download do Template Oficial

O fornecedor deve acessar a opção de envio de arquivo e baixar o template oficial.

O portal disponibiliza dois modelos:

template .xlsx;
template .csv.

Ambos devem conter as mesmas colunas oficiais:

Data_Envio
Distribuidor_Nome
Cidade_Filial
NFMAT
MATERIAL
Descrição
Ranking_Nacional
Qtd
Data_recebimento
Observacoes
Regra importante

O template oficial deve estar na pasta de templates do aplicativo. Arquivos da pasta samples devem ser usados apenas para teste interno.

Resultado esperado

O fornecedor baixa o template, preenche localmente e retorna ao portal para enviar o arquivo.

7. Etapa 4 — Envio do Arquivo de Forecast

A tela Enviar Arquivo concentra:

download dos templates oficiais;
orientação sobre colunas esperadas;
seleção do arquivo;
validação do arquivo;
retorno de sucesso ou erro.

O fornecedor pode enviar arquivos:

.xlsx;
.csv.

O arquivo não deve ser processado automaticamente ao ser selecionado. O fornecedor deve clicar em uma ação explícita, como:

Validar arquivo
Resultado esperado

Após clicar em validar, o app executa as validações e informa se o arquivo está válido ou inválido.

8. Etapa 5 — Validação do Arquivo

O portal valida automaticamente a estrutura e o conteúdo do arquivo.

Validações esperadas

O app deve validar:

extensão do arquivo;
arquivo vazio;
aba esperada no Excel;
colunas obrigatórias;
aliases de colunas aceitos;
material obrigatório;
filial/localidade obrigatória;
quantidade obrigatória;
quantidade numérica;
quantidade maior ou igual a zero;
data válida;
linhas totalmente vazias;
compatibilidade do fornecedor informado na planilha com o fornecedor logado, quando aplicável.
Se o arquivo for válido

O fornecedor deve receber mensagem simples, sem termos técnicos:

Arquivo válido para processamento.
Todas as validações foram aprovadas. O envio foi registrado e está disponível em Meus Envios.
Se o arquivo for inválido

O fornecedor deve receber mensagem clara:

Arquivo inválido.
Corrija os erros na planilha original e realize um novo envio.
9. Etapa 6 — Correção de Erros

Quando o arquivo contém inconsistências, o portal apresenta os erros encontrados.

Cada erro deve conter:

linha;
coluna;
valor informado;
erro identificado;
orientação de correção.

Exemplo:

Linha	Coluna	Valor informado	Erro	Orientação
15	MATERIAL	vazio	Campo obrigatório	Informar código do material
22	Qtd	ABC	Tipo inválido	Informar valor numérico
31	Data_recebimento	32/13/2026	Data inválida	Informar data válida

O fornecedor pode baixar o relatório de correção.

O botão deve ser apresentado de forma neutra:

Baixar relatório de correção

O app não deve alterar o arquivo original. O fornecedor corrige a planilha localmente e faz um novo envio.

10. Etapa 7 — Meus Envios

A tela Meus Envios concentra o histórico operacional do fornecedor.

Ela deve apresentar:

arquivos enviados;
versão de cada envio;
status;
data de envio;
linhas válidas;
linhas com erro;
ações disponíveis;
rastreabilidade operacional.
Informações esperadas
Campo	Descrição
Upload ID	Identificador do envio
Arquivo	Nome do arquivo enviado
Período	Período de referência do forecast
Versão	Número da versão do envio
Status	Situação do arquivo
Data de envio	Quando o arquivo foi enviado
Linhas válidas	Linhas aceitas
Linhas com erro	Linhas rejeitadas
Ação	Ver detalhe, ver erros ou cancelar
Status esperados
válido/ativo;
inválido;
substituído;
cancelado.
11. Etapa 8 — Versionamento

Cada novo envio cria uma nova versão.

A chave de versionamento é:

fornecedor + tipo de relatório + período
Regra de negócio

Quando o fornecedor envia um novo arquivo válido para o mesmo período:

o novo envio cria uma nova versão;
a nova versão válida se torna ativa;
a versão anterior permanece no histórico;
a versão anterior deixa de ser ativa ou fica marcada como substituída.
Upload inválido

Um upload inválido:

aparece no histórico;
permite consultar erros;
não substitui a versão válida ativa.
12. Etapa 9 — Detalhe do Envio

A tela de detalhe permite ao fornecedor consultar a rastreabilidade de um envio específico.

Ela deve mostrar apenas informações úteis ao fornecedor, como:

Upload ID;
fornecedor;
arquivo;
período;
versão;
status;
usuário que enviou;
data de envio;
total de linhas;
linhas válidas;
linhas com erro.
Informações que não devem aparecer para fornecedor

A tela do fornecedor não deve exibir:

Snowflake;
RAW;
STAGING;
TRUSTED;
camada destino;
DataFrame;
nomes técnicos de tabela;
botão de reprocessamento administrativo.

Essas informações são internas ou administrativas.

13. Etapa 10 — Cancelamento Lógico

O fornecedor pode cancelar um envio quando a regra permitir.

Condições esperadas

O cancelamento deve aparecer apenas para envios:

válidos;
ativos;
dentro da janela permitida.

Não deve aparecer para envios:

inválidos;
já cancelados;
substituídos;
fora da janela permitida.
Regra de cancelamento

O cancelamento é lógico.

Isso significa:

o registro não é excluído;
o status muda para cancelado;
o envio deixa de ser ativo;
o histórico é preservado;
o fornecedor pode visualizar o envio cancelado em Meus Envios.

Mensagem esperada:

Envio cancelado com sucesso. O registro foi mantido no histórico.
14. Regras Importantes da Jornada
14.1. O fornecedor oficial vem do login

Mesmo que a planilha contenha nome do fornecedor ou distribuidor, o fornecedor oficial deve ser identificado pelo usuário autenticado.

A planilha pode ser usada apenas para conferência.

14.2. O fornecedor vê apenas seus próprios dados

O fornecedor não deve acessar:

envios de outros fornecedores;
dados consolidados de todos;
telas administrativas;
cadastro de fornecedores;
painel completo do cliente.
14.3. O app não é uma ferramenta de edição

O fornecedor não edita dados diretamente no portal.

O fluxo correto é:

baixar template
↓
preencher/corrigir planilha localmente
↓
enviar novamente
14.4. O app não deve expor termos técnicos ao fornecedor

A jornada do fornecedor deve usar linguagem operacional.

Exemplos adequados:

Arquivo válido
Arquivo inválido
Corrigir planilha
Baixar relatório de correção
Ver meus envios
Ver detalhe
Cancelar envio

Exemplos que devem ser evitados na visão fornecedor:

Snowflake
RAW
STAGING
TRUSTED
DataFrame
Tabela destino
Camada destino
15. Resultado Esperado da Jornada

Ao final da jornada, o fornecedor deve conseguir:

acessar o portal;
baixar o template oficial;
preencher a planilha localmente;
enviar arquivo .xlsx ou .csv;
receber validação automática;
corrigir erros quando houver;
baixar relatório de correção;
reenviar arquivo corrigido;
acompanhar histórico e versões;
visualizar detalhes do envio;
cancelar envio quando permitido;
ter segurança de que visualiza apenas os próprios dados.
16. Critério de Aceite da Jornada do Fornecedor

A jornada pode ser considerada pronta quando os seguintes fluxos forem executados sem erro:

1. Entrar como fornecedor.
2. Visualizar dashboard inicial sem dados indevidos.
3. Baixar template XLSX.
4. Baixar template CSV.
5. Enviar arquivo válido.
6. Ver envio válido em Meus Envios.
7. Enviar arquivo inválido.
8. Ver erros do envio.
9. Baixar relatório de correção.
10. Reenviar arquivo corrigido.
11. Confirmar nova versão ativa.
12. Confirmar que upload inválido não substitui versão válida.
13. Cancelar envio permitido.
14. Confirmar envio cancelado no histórico.
15. Confirmar que fornecedor não vê telas administrativas.
Jornada resumida para apresentação
Fornecedor acessa o portal
↓
Consulta seu dashboard
↓
Baixa o template oficial
↓
Preenche o arquivo fora do app
↓
Envia o forecast
↓
App valida automaticamente
↓
Se houver erro, fornecedor baixa relatório e corrige
↓
Se estiver válido, envio entra no histórico
↓
Fornecedor acompanha versões, status e detalhes
↓
Fornecedor pode cancelar envio permitido