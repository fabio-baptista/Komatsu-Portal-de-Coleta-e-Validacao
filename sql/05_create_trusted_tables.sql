-- =============================================================================
-- 05_create_trusted_tables.sql
--
-- Tabela de dados validados e aprovados do Portal de Coleta.
-- Schema: TRUSTED
--
-- Tabelas:
--   TRUSTED.forecast_validated → dados finais prontos para consumo analítico
--
-- Propósito:
--   Camada final de dados aprovados. Contém apenas registros de uploads com
--   status VALID e is_active = TRUE (versão ativa do período).
--   Esta é a tabela a ser consumida por Power BI, DBT, ou outros processos.
--
-- Regra de atualização:
--   Quando um novo upload é aprovado para a mesma chave de versionamento
--   (supplier_id + report_type + reference_period), os registros anteriores
--   são marcados como is_active = FALSE e os novos são inseridos com
--   is_active = TRUE. Nenhum dado é excluído fisicamente (audit trail).
--
-- Chave funcional de unicidade lógica (não enforçada no Snowflake):
--   supplier_id + branch + material_code + forecast_period + upload_version
-- =============================================================================

USE DATABASE <YOUR_DATABASE>;
USE SCHEMA TRUSTED;


-- ---------------------------------------------------------------------------
-- TRUSTED.forecast_validated
-- Uma linha por combinação de fornecedor + filial + material + período,
-- para a versão ativa de cada upload.
-- Contém metadados completos de rastreabilidade: upload, versão, arquivo.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS TRUSTED.forecast_validated (

    record_id           NUMBER AUTOINCREMENT
        COMMENT 'Identificador sequencial do registro (gerado pelo Snowflake).',

    upload_id           VARCHAR(36)     NOT NULL
        COMMENT 'FK para CONTROL.upload_batches. Rastreia o upload de origem do dado.',

    -- Identificação do fornecedor — sempre do usuário logado, nunca da planilha
    supplier_id         VARCHAR(20)     NOT NULL
        COMMENT 'ID do fornecedor conforme cadastro em CONTROL.suppliers.',

    supplier_name       VARCHAR(255)    NOT NULL
        COMMENT 'Nome do fornecedor no momento do envio. Denormalizado para facilitar consultas.',

    -- Dados do forecast
    branch              VARCHAR(255)    NOT NULL
        COMMENT 'Filial ou localidade de referência do forecast.',

    material_code       VARCHAR(100)    NOT NULL
        COMMENT 'Código do material conforme sistema ERP/corporativo do cliente.',

    material_description VARCHAR(500)
        COMMENT 'Descrição do material. NULL se não informada no arquivo.',

    forecast_period     DATE            NOT NULL
        COMMENT 'Período de referência normalizado para o primeiro dia do mês (AAAA-MM-01). Exemplo: 2026-05-01.',

    forecast_quantity   NUMBER(15, 3)   NOT NULL
        COMMENT 'Quantidade prevista pelo fornecedor para o período.',

    -- Metadados de versão e rastreabilidade
    report_type         VARCHAR(100)    NOT NULL  DEFAULT 'Forecast DB'
        COMMENT 'Tipo de relatório de origem.',

    upload_version      NUMBER(4)       NOT NULL
        COMMENT 'Versão do upload dentro da chave supplier_id + report_type + reference_period.',

    is_active           BOOLEAN         NOT NULL  DEFAULT TRUE
        COMMENT 'TRUE para a versão vigente do período. FALSE para versões anteriores substituídas. Nunca exclui registros.',

    source_file_name    VARCHAR(500)    NOT NULL
        COMMENT 'Nome original do arquivo que gerou este registro.',

    uploaded_by         VARCHAR(255)    NOT NULL
        COMMENT 'E-mail do usuário que realizou o upload.',

    uploaded_at         TIMESTAMP_NTZ   NOT NULL
        COMMENT 'Data/hora do upload que originou este registro.',

    validated_at        TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora em que o registro foi promovido para a camada TRUSTED.',

    CONSTRAINT pk_forecast_validated PRIMARY KEY (record_id)
);
