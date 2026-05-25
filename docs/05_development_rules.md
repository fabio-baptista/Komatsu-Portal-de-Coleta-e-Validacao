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