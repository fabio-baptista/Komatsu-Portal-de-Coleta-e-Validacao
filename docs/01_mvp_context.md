# MVP - Portal de Coleta e Validação de Forecast

O projeto consiste em um aplicativo em Streamlit para coleta de arquivos de forecast enviados por fornecedores/distribuidores.

O app deve permitir:
- login por perfil fornecedor/admin;
- download de template;
- upload de arquivos .xlsx e .csv;
- validação automática;
- geração de relatório de erros;
- histórico de envios;
- versionamento;
- cancelamento lógico dentro da janela permitida;
- visão administrativa de fornecedores, pendências e dados validados;
- gravação futura no Snowflake.

O app é operacional, não é BI.
O foco é ingestão, validação, rastreabilidade e disponibilização dos dados.