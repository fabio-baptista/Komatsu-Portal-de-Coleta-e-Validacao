-- =============================================================================
-- 01_create_schemas.sql
--
-- Cria os schemas lógicos do Portal de Coleta e Validação de Forecast.
-- Executar com um usuário que tenha privilégio SYSADMIN ou equivalente.
--
-- Substituir <YOUR_DATABASE> pelo nome real do banco de dados antes de executar.
--
-- Arquitetura de schemas:
--   CONTROL  → metadados operacionais (usuários, fornecedores, janelas, uploads)
--   RAW      → dados brutos recebidos do arquivo, sem transformação
--   STAGING  → dados normalizados e validados, prontos para promoção
--   TRUSTED  → dados aprovados, disponíveis para consumo analítico
-- =============================================================================

USE DATABASE <YOUR_DATABASE>;  -- substituir pelo banco do cliente

-- ---------------------------------------------------------------------------
-- CONTROL: metadados operacionais do portal
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS CONTROL
    COMMENT = 'Metadados operacionais: usuários, fornecedores, janelas de envio e controle de uploads.';

-- ---------------------------------------------------------------------------
-- RAW: dados brutos do arquivo enviado, sem transformação
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS RAW
    COMMENT = 'Dados brutos recebidos dos fornecedores, preservados sem modificação.';

-- ---------------------------------------------------------------------------
-- STAGING: dados normalizados e validados, aguardando promoção
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS STAGING
    COMMENT = 'Dados normalizados após validação. Intermediário entre RAW e TRUSTED.';

-- ---------------------------------------------------------------------------
-- TRUSTED: dados aprovados, disponíveis para consumo e análise
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS TRUSTED
    COMMENT = 'Dados validados e aprovados, disponíveis para consumo analítico.';
