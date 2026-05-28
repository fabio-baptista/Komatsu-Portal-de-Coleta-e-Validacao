Preencha o arquivo docs/06_snowflake_deployment_notes.md com notas técnicas para futura publicação no Streamlit in Snowflake.

Incluir:
1. O app será desenvolvido localmente e depois publicado no Snowflake;
2. Uso futuro de Snowflake CLI;
3. Necessidade de database, schema, warehouse, stage e objeto Streamlit;
4. Uso de App Viewer URL;
5. Usuários fornecedores precisarão de identidade Snowflake ou IdP reconhecida;
6. Roles devem restringir acesso apenas ao app;
7. O app usará usuário autenticado para identificar perfil e fornecedor;
8. O cadastro operacional do app é separado da identidade Snowflake/IdP;
9. Para MVP local, dados podem ser mockados;
10. Integração real com Snowflake será feita em etapa posterior.

Não criar comandos definitivos ainda.
Não assumir nomes reais de database, warehouse ou roles.

---

## Variáveis de Ambiente para Deploy

### APP_ENV

| Ambiente | Valor | Efeito |
|----------|-------|--------|
| Desenvolvimento local | `dev` (default) | Ferramentas de teste habilitadas |
| Testes automatizados | `test` | Idem |
| Streamlit in Snowflake (prod) | `production` | Ferramentas de teste ocultas e bloqueadas |

**Obrigatório em produção**: definir `APP_ENV=production` antes de publicar o app.

### SNOWFLAKE_CONNECTION_NAME

Usado apenas em execução local. Define qual conexão de `~/.snowflake/connections.toml` o Snowpark usa para criar sessão.

- Default: `KOMATSU_BRAZIL_INTERNATIONAL_PAT`
- Em Streamlit in Snowflake: não se aplica (sessão via `get_active_session()`)

### Checklist de deploy para produção

- [ ] `APP_ENV=production` configurado
- [ ] Database, schema, warehouse e role revisados
- [ ] Botão "Limpar dados de teste" não aparece na UI
- [ ] `clear_dev_data()` recusa execução
- [ ] Dados seed/base validados (5 suppliers, 6 users, 1 submission window)
- [ ] Credenciais de desenvolvimento removidas/rotacionadas
- [ ] `DEMO_MODE=False` confirmado