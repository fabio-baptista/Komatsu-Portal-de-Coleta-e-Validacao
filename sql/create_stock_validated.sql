-- =============================================================================
-- DDL: TRUSTED.STOCK_VALIDATED
-- Tabela de estoque validado para o Portal Komatsu de Coleta e Validação.
-- 
-- NÃO EXECUTAR AUTOMATICAMENTE — requer autorização do DBA/owner.
-- Criado em: 2026-06-11
-- =============================================================================

CREATE TABLE IF NOT EXISTS KBI_DATA_JOURNEY_DEV_DB.TRUSTED.STOCK_VALIDATED (
    ROW_ID                STRING        NOT NULL,
    SUPPLIER_ID           STRING        NOT NULL,
    SUPPLIER_NAME         STRING        NOT NULL,
    BRANCH                STRING        NOT NULL,
    MATERIAL_CODE         STRING        NOT NULL,
    MATERIAL_DESCRIPTION  STRING,
    STOCK_QUANTITY        NUMBER(18, 4) NOT NULL,
    UNIT_COST             NUMBER(18, 4) NOT NULL,
    TOTAL_COST            NUMBER(18, 4),
    PURCHASE_DATE         DATE,
    LAST_SALE_DATE        DATE,
    INVOICE_NUMBER        STRING,
    STOCK_YEAR            NUMBER(4, 0),
    STOCK_MONTH           NUMBER(2, 0),
    UPLOAD_ID             STRING        NOT NULL,
    UPLOAD_VERSION        NUMBER(10, 0) NOT NULL,
    UPLOADED_AT           TIMESTAMP_NTZ NOT NULL,
    SOURCE_FILE_NAME      STRING        NOT NULL,
    IS_ACTIVE             BOOLEAN       NOT NULL DEFAULT TRUE,
    CREATED_AT            TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()
);

-- Índices sugeridos (opcional)
-- CREATE INDEX IF NOT EXISTS idx_stock_supplier ON KBI_DATA_JOURNEY_DEV_DB.TRUSTED.STOCK_VALIDATED (SUPPLIER_ID, IS_ACTIVE);
-- CREATE INDEX IF NOT EXISTS idx_stock_upload ON KBI_DATA_JOURNEY_DEV_DB.TRUSTED.STOCK_VALIDATED (UPLOAD_ID);
