-- =============================================================================
-- 04_create_staging_tables.sql
--
-- Tabela de dados normalizados do Portal de Coleta e Validação.
-- Schema: STAGING
--
-- Tabelas:
--   STAGING.forecast_normalized → linhas validadas e normalizadas,
--                                  com colunas canônicas e tipos corretos
--
-- Propósito:
--   Camada intermediária entre RAW e TRUSTED.
--   Contém apenas as linhas que passaram pelas validações de estrutura,
--   tipo e obrigatoriedade. Datas estão em ISO 8601. Quantidades são NUMBER.
--   Nomes de fornecedor vêm do usuário logado — nunca da planilha.
--
-- Chave funcional do forecast (unicidade lógica, não enforçada):
--   supplier_id + branch + material_code + forecast_period + upload_version
-- =============================================================================

USE DATABASE <YOUR_DATABASE>;
USE SCHEMA STAGING;


-- ---------------------------------------------------------------------------
-- STAGING.forecast_normalized
-- Uma linha por linha válida do arquivo, com campos canônicos.
-- Mantém referência ao upload de origem para rastreabilidade.
-- Linhas com erros NÃO são promovidas para esta tabela.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS STAGING.forecast_normalized (

    staging_id          NUMBER AUTOINCREMENT
        COMMENT 'Identificador sequencial da linha normalizada (gerado pelo Snowflake).',

    upload_id           VARCHAR(36)     NOT NULL
        COMMENT 'FK para CONTROL.upload_batches. Rastreia a origem do dado.',

    -- Identificação do fornecedor — sempre do usuário logado, nunca da planilha
    supplier_id         VARCHAR(20)     NOT NULL
        COMMENT 'ID do fornecedor conforme cadastro em CONTROL.suppliers. Definido pelo login, não pelo arquivo.',

    supplier_name       VARCHAR(255)    NOT NULL
        COMMENT 'Nome do fornecedor no momento do envio. Denormalizado para rastreabilidade.',

    -- Dados do forecast (canônicos — nomes padronizados independente do alias no arquivo)
    branch              VARCHAR(255)    NOT NULL
        COMMENT 'Filial ou localidade de referência do forecast.',

    material_code       VARCHAR(100)    NOT NULL
        COMMENT 'Código do material conforme sistema ERP/corporativo do cliente.',

    material_description VARCHAR(500)
        COMMENT 'Descrição do material. Preenchida se presente no arquivo; NULL caso contrário.',

    forecast_period     DATE            NOT NULL
        COMMENT 'Período de referência do forecast normalizado para o primeiro dia do mês (AAAA-MM-01).',

    forecast_quantity   NUMBER(15, 3)   NOT NULL
        COMMENT 'Quantidade prevista. Normalizada para NUMBER; vírgulas convertidas para pontos.',

    -- Metadados do upload
    report_type         VARCHAR(100)    NOT NULL  DEFAULT 'Forecast DB'
        COMMENT 'Tipo de relatório de origem.',

    upload_version      NUMBER(4)       NOT NULL
        COMMENT 'Versão do upload dentro da chave supplier_id + report_type + reference_period.',

    source_file_name    VARCHAR(500)    NOT NULL
        COMMENT 'Nome original do arquivo de origem.',

    row_number_in_file  NUMBER(10)
        COMMENT 'Número da linha no arquivo original (para rastreabilidade).',

    normalized_at       TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora em que a linha foi normalizada e inserida na camada STAGING.',

    CONSTRAINT pk_forecast_normalized PRIMARY KEY (staging_id)
);
