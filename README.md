# Portal Komatsu — Coleta e Validação de Forecast

Portal web para coleta, validação e rastreabilidade de arquivos de forecast enviados por fornecedores.

---

## Como executar

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

---

## Autenticação no MVP local

> **Importante:** A autenticação atual é **simulada** para o ambiente de desenvolvimento local (MVP).

### Como funciona hoje

- O login é feito por botão de perfil: **Fornecedor** ou **Administrativo**.
- Não há senha, token, hash ou banco de usuários.
- Os dados do usuário logado (nome, e-mail, `supplier_id`, perfil) são carregados de `app/services/mock_data_service.py`.
- O controle de acesso por perfil é aplicado localmente no roteador (`app/streamlit_app.py`), impedindo que um fornecedor acesse telas administrativas mesmo que manipule o estado da sessão.

### Perfis disponíveis no MVP

| Perfil | `role` | `supplier_id` | Acesso |
|---|---|---|---|
| Fornecedor | `supplier` | `SUP001` | Home, Upload, Histórico, Erros, Detalhe do Envio |
| Administrador | `admin` | `None` | Painel, Fornecedores, Dados Validados, Detalhe do Envio |

### Evolução prevista

A autenticação real será implementada na integração com Snowflake ou IdP aprovado pelo cliente. O arquivo `app/services/auth_service.py` está reservado para essa evolução e já conta com funções stub documentadas:

- `get_current_role()` — retorna o perfil do usuário logado
- `get_current_user()` — retorna dados básicos do usuário logado
- `is_admin()` / `is_supplier()` — verificações de perfil
- `is_authenticated()` — verifica se há sessão ativa

Nenhuma dessas funções é chamada automaticamente pelo app no MVP — o estado de sessão é gerenciado diretamente em `app/utils/session_state.py`.

---

## Estrutura do projeto

```
app/
  streamlit_app.py        # Entry point e roteador
  pages/
    supplier_home.py      # (reservado)
    supplier_upload.py    # Upload de forecast
    supplier_history.py   # Histórico de envios
    supplier_errors.py    # Erros de validação
    admin_upload_detail.py# Detalhe do envio (compartilhado, role-aware)
    admin_dashboard.py    # Painel admin
    admin_suppliers.py    # Gestão de fornecedores
    validated_data.py     # Dados validados
  components/
    navigation.py         # Sidebar com menu por perfil
    cards.py              # Cards de métricas
    tables.py             # Tabelas HTML reutilizáveis
    badges.py             # Badges de status/versão
    layout.py             # CSS, header, footer
  services/
    auth_service.py       # Stub de autenticação (evolução futura)
    upload_service.py     # Serviço de uploads (mock + sessão)
    validation_service.py # Regras de validação do arquivo
    forecast_service.py   # Normalização para esquema alvo
    mock_data_service.py  # Dados fictícios centralizados
    snowflake_service.py  # (reservado para integração real)
    supplier_service.py   # (reservado)
  utils/
    session_state.py      # Gerenciamento centralizado do session_state
    file_reader.py        # Leitura de .xlsx e .csv
    constants.py          # Aliases de colunas e constantes
    dates.py              # Utilitários de data
  templates/
    template_forecast.xlsx# Template oficial para download pelo fornecedor
samples/
  forecast_teste_01_valido.csv  # Arquivo de teste manual válido
  template_forecast.xlsx        # Cópia do template (referência)
```

---

## Arquivo de teste

Para testar o upload manualmente, use:

```
samples/forecast_teste_01_valido.csv
```

Contém 5 linhas válidas com as colunas esperadas pelo validador.
