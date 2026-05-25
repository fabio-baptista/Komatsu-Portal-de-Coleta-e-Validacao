-- =============================================================================
-- 03_create_raw_tables.sql
--
-- Tabela de dados brutos do Portal de Coleta e Validação.
-- Schema: RAW
--
-- Tabelas:
--   RAW.uploaded_file_rows → cada linha do arquivo enviado, preservada sem transformação
--
-- Propósito:
--   Preservar exatamente o que o fornecedor enviou, antes de qualquer
--   validação ou normalização. Permite reprocessamento e auditoria completa.
--
-- NOTA: O campo extra_columns armazena colunas adicionais não previstas
--       no template (VARIANT). Não deve ser usado para consultas operacionais.
-- =============================================================================

USE DATABASE <YOUR_DATABASE>;
USE SCHEMA RAW;


-- ---------------------------------------------------------------------------
-- RAW.uploaded_file_rows
-- Uma linha por linha do arquivo original.
-- Os campos raw_* preservam exatamente o valor enviado pelo fornecedor,
-- incluindo formatações inconsistentes, textos inválidos e nulos.
-- O campo raw_supplier_name é extraído da planilha apenas para
-- conferência de compatibilidade — o fornecedor oficial é o do login.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS RAW.uploaded_file_rows (

    row_id              NUMBER AUTOINCREMENT
        COMMENT 'Identificador sequencial da linha (gerado pelo Snowflake).',

    upload_id           VARCHAR(36)     NOT NULL
        COMMENT 'FK para CONTROL.upload_batches. Liga cada linha ao seu upload.',

    row_number          NUMBER(10)      NOT NULL
        COMMENT 'Número da linha no arquivo original (cabeçalho = 0, dados a partir de 1).',

    -- Campos brutos — preservam o valor original do arquivo sem transformação
    raw_material        VARCHAR(500)
        COMMENT 'Valor bruto da coluna de material (código ou descrição). Pode conter aliases do template.',

    raw_branch          VARCHAR(500)
        COMMENT 'Valor bruto da coluna de filial/localidade.',

    raw_quantity        VARCHAR(200)
        COMMENT 'Valor bruto da coluna de quantidade. Pode ser texto inválido, negativo ou vazio.',

    raw_date            VARCHAR(200)
        COMMENT 'Valor bruto da coluna de data de recebimento. Pode conter formatos variados ou datas inválidas.',

    raw_supplier_name   VARCHAR(500)
        COMMENT 'Valor bruto da coluna de fornecedor, se presente no arquivo. Usado apenas para conferência cruzada — o fornecedor oficial vem do usuário logado.',

    extra_columns       VARIANT
        COMMENT 'Colunas adicionais não mapeadas no template, armazenadas como JSON. Preserva colunas extras sem perda.',

    loaded_at           TIMESTAMP_NTZ   NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Data/hora em que a linha foi carregada na camada RAW.',

    CONSTRAINT pk_uploaded_file_rows PRIMARY KEY (row_id)
);
