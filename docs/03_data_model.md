Preencha o arquivo docs/03_data_model.md com o modelo lógico de dados previsto para o MVP.

O documento deve conter:
1. Schemas lógicos: CONTROL, RAW, STAGING, TRUSTED;
2. Tabelas previstas:
   - CONTROL.users
   - CONTROL.suppliers
   - CONTROL.upload_batches
   - CONTROL.validation_errors
   - CONTROL.submission_windows
   - RAW.uploaded_file_rows
   - STAGING.forecast_normalized
   - TRUSTED.forecast_validated
3. Finalidade de cada tabela;
4. Campos mínimos sugeridos;
5. Observação de que estruturas existentes no Snowflake do cliente devem ser reaproveitadas quando disponíveis;
6. Regra de que o fornecedor oficial vem do login, não da planilha;
7. Chave funcional do forecast:
   fornecedor + filial/localidade + material + período.

Não criar SQL ainda.
Não inventar campos excessivos.
Manter objetivo e prático.