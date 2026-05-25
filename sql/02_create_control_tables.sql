-- =============================================================================
-- 02_create_control_tables.sql
--
-- Tabelas de controle operacional do Portal de Coleta e Validação.
-- Schema: CONTROL
--
-- Tabelas:
--   CONTROL.users              → usuários do portal (admins e fornecedores)
--   CONTROL.suppliers          → fornecedores cadastrados
--   CONTROL.upload_batches     → registro de cada arquivo enviado
--   CONTROL.validation_errors  → erros encontrados por upload
--   CONTROL.submission_windows → janelas de envio por período/relatório
--
-- NOTA: Chaves primárias em Snowflake são declarativas e não enforçadas.
--       A integridade referencial deve ser garantida pela aplicação.
-- =============================================================================

USE DATABASE <YOUR_DATABASE>;
USE SCHEMA CONTROL;


-- ---------------------------------------------------------------------------
-- CONTROL.users
-- Usuários do portal. Cada usuário está vinculado a um fornecedor
-- (role = 'supplier') ou é administrador (role = 'admin').
-- O fornecedor oficial de um envio é definido pelo usuário logado,
-- nunca pelo conteúdo da planilha.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CONTROL.users (

    user_id         VARCHAR(36)     NOT NULL    -- UUID do usuário
        COMMENT 'Identificador único do usuário (UUID v4).',

    email           VARCHAR(255)    NOT NULL    -- e-mail de login (único)
        COMMENT 'E-mail de acesso ao portal. Deve ser único.',

    full_name       VARCHAR(255)    NOT NULL    -- nome completo
        COMMENT 'Nome completo do usuário exibido no portal.',

    role            VARCHAR(20)     NOT NULL    -- 'supplier' | 'admin'
        COMMENT 'Perfil de acesso: supplier (fornecedor) ou admin.',

    supplier_id     VARCHAR(20)              -- FK → CONTROL.suppliers (nulo para admin)
        COMMENT 'ID do fornecedor vinculado. NULL para perfil admin.',

    is_active       BOOLEAN         NOT NULL  DEFAULT TRUE
        COMMENT 'Indica se o usuário está ativo no portal.',

    created_at      TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora de criação do registro.',

    updated_at      TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora da última atualização.',

    CONSTRAINT pk_users PRIMARY KEY (user_id)
);


-- ---------------------------------------------------------------------------
-- CONTROL.suppliers
-- Fornecedores cadastrados no portal.
-- NOTA: Se o cliente já possuir cadastro corporativo de fornecedores
--       no Snowflake, esta tabela pode ser substituída por uma VIEW
--       ou referência à estrutura existente.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CONTROL.suppliers (

    supplier_id     VARCHAR(20)     NOT NULL    -- código único do fornecedor
        COMMENT 'Código único do fornecedor (ex: SUP001). Deve coincidir com o sistema corporativo, se existir.',

    supplier_name   VARCHAR(255)    NOT NULL    -- nome comercial
        COMMENT 'Nome comercial do fornecedor exibido no portal.',

    cnpj            VARCHAR(18)                 -- CNPJ no formato XX.XXX.XXX/XXXX-XX (opcional)
        COMMENT 'CNPJ do fornecedor. Campo informativo, não validado pelo portal.',

    status          VARCHAR(20)     NOT NULL  DEFAULT 'active'
        COMMENT 'Status do cadastro: active | inactive.',

    is_expected     BOOLEAN         NOT NULL  DEFAULT TRUE
        COMMENT 'Indica se o fornecedor deve enviar forecast no ciclo atual.',

    created_at      TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora de criação do registro.',

    updated_at      TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora da última atualização.',

    CONSTRAINT pk_suppliers PRIMARY KEY (supplier_id)
);


-- ---------------------------------------------------------------------------
-- CONTROL.upload_batches
-- Registro de cada arquivo enviado pelo fornecedor.
-- Cada linha representa um upload, com metadados de versão, status e auditoria.
--
-- Chave de versionamento funcional (não enforçada): supplier_id + report_type + reference_period
-- A versão ativa é identificada por is_active = TRUE.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CONTROL.upload_batches (

    upload_id           VARCHAR(36)     NOT NULL
        COMMENT 'Identificador único do upload (UUID v4 em produção).',

    supplier_id         VARCHAR(20)     NOT NULL
        COMMENT 'ID do fornecedor que realizou o envio. Vem do usuário logado, nunca da planilha.',

    supplier_name       VARCHAR(255)    NOT NULL
        COMMENT 'Nome do fornecedor no momento do envio. Denormalizado para rastreabilidade histórica.',

    report_type         VARCHAR(100)    NOT NULL  DEFAULT 'Forecast DB'
        COMMENT 'Tipo de relatório enviado (ex: Forecast DB). Compõe a chave de versionamento.',

    reference_period    VARCHAR(7)      NOT NULL
        COMMENT 'Período de referência do forecast no formato AAAA-MM (ex: 2026-05). Compõe a chave de versionamento.',

    upload_version      NUMBER(4)       NOT NULL  DEFAULT 1
        COMMENT 'Número sequencial da versão dentro da chave supplier_id + report_type + reference_period.',

    version_key         VARCHAR(200)    NOT NULL
        COMMENT 'Chave composta de versionamento: supplier_id|report_type|reference_period. Facilita queries de versão ativa.',

    status              VARCHAR(20)     NOT NULL
        COMMENT 'Status do upload: VALID | INVALID | REPLACED | CANCELLED.',

    is_active           BOOLEAN         NOT NULL  DEFAULT FALSE
        COMMENT 'TRUE apenas para o upload VALID vigente dentro da version_key. Facilita filtros de versão ativa.',

    file_name           VARCHAR(500)    NOT NULL
        COMMENT 'Nome original do arquivo enviado pelo fornecedor.',

    total_rows          NUMBER(10)      NOT NULL  DEFAULT 0
        COMMENT 'Total de linhas de dados no arquivo (excluindo cabeçalho e linhas vazias).',

    valid_rows          NUMBER(10)      NOT NULL  DEFAULT 0
        COMMENT 'Linhas sem nenhum erro de validação.',

    invalid_rows        NUMBER(10)      NOT NULL  DEFAULT 0
        COMMENT 'Linhas com pelo menos um erro de validação.',

    uploaded_by         VARCHAR(255)    NOT NULL
        COMMENT 'E-mail do usuário que realizou o envio.',

    uploaded_at         TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora do recebimento do arquivo.',

    cancelled_at        TIMESTAMP_NTZ
        COMMENT 'Data/hora do cancelamento lógico. NULL se não cancelado.',

    cancelled_by        VARCHAR(255)
        COMMENT 'E-mail do usuário que realizou o cancelamento. NULL se não cancelado.',

    cancel_reason       VARCHAR(1000)
        COMMENT 'Motivo informado para o cancelamento. Texto livre, opcional.',

    source_system       VARCHAR(100)    DEFAULT 'portal_web'
        COMMENT 'Sistema de origem do upload (portal_web, api, etc.).',

    CONSTRAINT pk_upload_batches PRIMARY KEY (upload_id)
);


-- ---------------------------------------------------------------------------
-- CONTROL.validation_errors
-- Erros encontrados durante a validação de um arquivo.
-- Um upload pode ter zero ou múltiplos erros.
-- Uploads com erro (status = INVALID) têm ao menos um registro aqui.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CONTROL.validation_errors (

    error_id            NUMBER AUTOINCREMENT
        COMMENT 'Identificador sequencial do erro (gerado pelo Snowflake).',

    upload_id           VARCHAR(36)     NOT NULL
        COMMENT 'FK para CONTROL.upload_batches. Identifica o upload com erro.',

    row_number          NUMBER(10)      NOT NULL  DEFAULT 0
        COMMENT 'Número da linha no arquivo onde o erro foi encontrado. 0 indica erro de estrutura (coluna ausente).',

    column_name         VARCHAR(200)    NOT NULL
        COMMENT 'Nome da coluna onde o erro foi detectado (nome canônico ou nome real do arquivo).',

    value_informed      VARCHAR(1000)
        COMMENT 'Valor que causou o erro. "(vazio)" se o campo estava em branco.',

    error_type          VARCHAR(100)    NOT NULL
        COMMENT 'Classificação do erro (ex: Campo obrigatório, Tipo inválido, Data inválida, Valor negativo).',

    correction_guidance VARCHAR(500)
        COMMENT 'Instrução de correção exibida ao fornecedor.',

    created_at          TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora em que o erro foi registrado.',

    CONSTRAINT pk_validation_errors PRIMARY KEY (error_id)
);


-- ---------------------------------------------------------------------------
-- CONTROL.submission_windows
-- Janelas de envio configuradas por período e tipo de relatório.
-- Controla quando os fornecedores podem enviar ou cancelar arquivos.
-- O app valida o período do upload contra a janela aberta.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS CONTROL.submission_windows (

    window_id           NUMBER AUTOINCREMENT
        COMMENT 'Identificador sequencial da janela.',

    report_type         VARCHAR(100)    NOT NULL  DEFAULT 'Forecast DB'
        COMMENT 'Tipo de relatório para o qual a janela se aplica.',

    reference_period    VARCHAR(7)      NOT NULL
        COMMENT 'Período de referência da janela no formato AAAA-MM (ex: 2026-05).',

    label               VARCHAR(100)    NOT NULL
        COMMENT 'Rótulo amigável exibido no portal (ex: Maio/2026).',

    open_at             TIMESTAMP_NTZ   NOT NULL
        COMMENT 'Data/hora de abertura da janela de envio.',

    closes_at           TIMESTAMP_NTZ   NOT NULL
        COMMENT 'Data/hora de encerramento da janela de envio.',

    is_open             BOOLEAN         NOT NULL  DEFAULT FALSE
        COMMENT 'Indica se a janela está aberta no momento. Atualizada por processo agendado ou manualmente pelo admin.',

    created_at          TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora de criação do registro.',

    created_by          VARCHAR(255)
        COMMENT 'E-mail do admin que criou a janela.',

    CONSTRAINT pk_submission_windows PRIMARY KEY (window_id),
    CONSTRAINT uq_submission_windows UNIQUE (report_type, reference_period)
);
