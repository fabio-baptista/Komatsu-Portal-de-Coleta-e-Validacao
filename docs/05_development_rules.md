# Regras de Desenvolvimento

1. Não implementar funcionalidades fora do MVP.
2. Não criar backend externo.
3. Não criar banco local permanente.
4. Não criar autenticação real nesta primeira etapa.
5. Não conectar no Snowflake sem autorização explícita.
6. Não implementar BI ou gráficos analíticos avançados.
7. Não permitir edição linha a linha dos dados no MVP.
8. O fornecedor deve corrigir o arquivo localmente e reenviar.
9. O fornecedor oficial vem do usuário logado, não da planilha.
10. O app deve ser modularizado.
11. Evitar código monolítico em streamlit_app.py.
12. Separar UI, serviços, validações e utilitários.
13. Toda tela deve usar dados fictícios até a etapa de integração.
14. Todo código deve ser simples, legível e comentado apenas quando necessário.
15. Antes de alterar muitos arquivos, apresentar plano de alteração.
16. Não fazer refatorações grandes sem pedido explícito.
17. Não apagar arquivos sem autorização.
18. Não criar dependências desnecessárias.
19. Priorizar pandas, streamlit e bibliotecas padrão.
20. Manter layout aderente à identidade visual Komatsu: azul marinho, branco, amarelo e cinza claro.

---

## Decisão Arquitetural: Ferramentas de DEV/TESTE

### Contexto
O projeto está em ambiente de desenvolvimento. Dados de teste são persistidos no Snowflake durante o desenvolvimento do MVP. Para facilitar ciclos de teste, existe um botão "Limpar dados de teste" que remove dados criados pelo app sem afetar dados seed/base.

### Diretriz
- O botão "Limpar dados de teste" é uma ferramenta **exclusiva de DEV/TESTE**. Não faz parte da operação de produção.
- Em DEV/TESTE/LOCAL: o botão pode aparecer (controlado por `APP_ENV`).
- Em PRODUÇÃO: o botão **não deve aparecer** e a função `clear_dev_data()` **bloqueia execução**.
- A variável `APP_ENV` (definida em `app/utils/constants.py`) é lida de `os.environ.get("APP_ENV", "dev")`.
- O código deve **evitar sucesso falso** e deve **mostrar erro real** caso a limpeza falhe.
- A limpeza **preserva dados seed/base** (IDs `s-NNN`, `u-NNN`, `w-NNN`) e remove apenas dados criados pelo app (IDs UUID).

### Obrigatoriedade antes de produção
Antes de promover o projeto para produção, será obrigatório:
1. Configurar `APP_ENV=production`.
2. Revisar variáveis de database, schema, warehouse e role.
3. Confirmar que o botão "Limpar dados" não aparece na UI.
4. Validar que `clear_dev_data()` recusa execução com `APP_ENV=production`.