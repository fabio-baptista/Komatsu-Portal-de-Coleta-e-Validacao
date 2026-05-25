"""
snowflake_service.py

Camada de abstração para acesso ao Snowflake.
Compatível com execução local e com Streamlit in Snowflake.

Comportamento por ambiente:
  - Streamlit in Snowflake  → usa get_active_session() do Snowpark (sem credenciais)
  - Execução local           → todas as funções retornam None/False e logam aviso
                               O app continua operando com dados mockados normalmente

Regras:
  - Sem credenciais no código.
  - Sem uso de secrets nesta fase.
  - Falha controlada: nenhuma exceção propaga para a UI.
  - is_running_in_snowflake() é o ponto de decisão em toda a aplicação.

Uso típico no app:
  if is_running_in_snowflake():
      session = get_snowflake_session()
      df = read_table(session, "TRUSTED.forecast_validated")
  else:
      df = pd.DataFrame(get_mock_validated_forecast())
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Detecção de ambiente
# ---------------------------------------------------------------------------

def is_running_in_snowflake() -> bool:
    """
    Retorna True se o app está rodando dentro do Streamlit in Snowflake.

    A detecção usa a presença do módulo snowflake.snowpark e a disponibilidade
    de get_active_session() sem lançar exceção — indicativo do ambiente SiS.

    Localmente, o Snowpark não está disponível ou a sessão ativa não existe,
    então retorna False silenciosamente.
    """
    try:
        from snowflake.snowpark.context import get_active_session
        session = get_active_session()
        return session is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Obtenção de sessão
# ---------------------------------------------------------------------------

def get_snowflake_session():
    """
    Retorna a sessão Snowpark ativa quando rodando em Streamlit in Snowflake.
    Retorna None se o ambiente não for Snowflake ou se ocorrer qualquer erro.

    Não aceita parâmetros de conexão — a sessão é gerenciada pelo ambiente SiS.
    Para uso externo (Snowflake Connector, etc.), esta função não é adequada.

    Retorno:
        snowflake.snowpark.Session | None
    """
    if not is_running_in_snowflake():
        logger.debug(
            "[snowflake_service] Execução local detectada. "
            "Sessão Snowflake não disponível."
        )
        return None

    try:
        from snowflake.snowpark.context import get_active_session
        return get_active_session()
    except Exception as exc:
        logger.warning(
            "[snowflake_service] Falha ao obter sessão Snowflake: %s", exc
        )
        return None


# ---------------------------------------------------------------------------
# Informações do usuário conectado
# ---------------------------------------------------------------------------

def get_current_snowflake_user() -> Optional[str]:
    """
    Retorna o nome do usuário Snowflake conectado (CURRENT_USER()).
    Retorna None se não estiver rodando no Snowflake.

    Uso: exibir o usuário autenticado no painel admin quando em produção.

    Retorno:
        str (login do usuário Snowflake) | None
    """
    session = get_snowflake_session()
    if session is None:
        return None

    try:
        result = session.sql("SELECT CURRENT_USER() AS user_name").collect()
        if result:
            return result[0]["USER_NAME"]
        return None
    except Exception as exc:
        logger.warning(
            "[snowflake_service] Falha ao obter usuário Snowflake: %s", exc
        )
        return None


# ---------------------------------------------------------------------------
# Execução de queries
# ---------------------------------------------------------------------------

def execute_query(
    query: str,
    params: Optional[dict] = None,
) -> Optional[pd.DataFrame]:
    """
    Executa uma query SQL no Snowflake e retorna um DataFrame.
    Retorna None se não estiver rodando no Snowflake ou se ocorrer erro.

    Parâmetros:
        query  — SQL a executar. Use :param_name para parâmetros nomeados.
        params — dict com valores para substituição segura (evita SQL injection).
                 Substituição é feita manualmente pois o Snowpark não suporta
                 bind parameters no método sql(). Sanitize os valores antes de usar.

    Retorno:
        pd.DataFrame com os resultados | None

    Exemplo:
        df = execute_query("SELECT * FROM TRUSTED.forecast_validated WHERE supplier_id = :sid",
                           params={"sid": "SUP001"})

    AVISO: A substituição de params é feita com replace simples.
           Para produção, valide os parâmetros antes de montar a query.
    """
    session = get_snowflake_session()
    if session is None:
        logger.debug(
            "[snowflake_service] execute_query ignorado — sem sessão Snowflake."
        )
        return None

    # Substituição segura de parâmetros nomeados (:nome → valor)
    final_query = query
    if params:
        for key, value in params.items():
            placeholder = f":{key}"
            if isinstance(value, str):
                safe_value = f"'{value.replace(chr(39), chr(39) * 2)}'"
            elif value is None:
                safe_value = "NULL"
            else:
                safe_value = str(value)
            final_query = final_query.replace(placeholder, safe_value)

    try:
        result = session.sql(final_query).to_pandas()
        return result
    except Exception as exc:
        logger.error(
            "[snowflake_service] Erro ao executar query: %s\nQuery: %s",
            exc, final_query[:200],
        )
        return None


# ---------------------------------------------------------------------------
# Leitura de tabelas
# ---------------------------------------------------------------------------

def read_table(
    table_name: str,
    limit: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Lê uma tabela ou view do Snowflake e retorna um DataFrame.
    Retorna None se não estiver rodando no Snowflake ou se ocorrer erro.

    Parâmetros:
        table_name — nome qualificado da tabela (ex: "TRUSTED.forecast_validated")
        limit      — número máximo de linhas a retornar. None = sem limite.

    Retorno:
        pd.DataFrame | None

    Exemplo:
        df = read_table("TRUSTED.forecast_validated", limit=1000)
        if df is None:
            # fallback para dados mock
            df = pd.DataFrame(get_mock_validated_forecast())
    """
    session = get_snowflake_session()
    if session is None:
        logger.debug(
            "[snowflake_service] read_table(%s) ignorado — sem sessão Snowflake.",
            table_name,
        )
        return None

    limit_clause = f" LIMIT {int(limit)}" if limit else ""
    query = f"SELECT * FROM {table_name}{limit_clause}"

    try:
        return session.sql(query).to_pandas()
    except Exception as exc:
        logger.error(
            "[snowflake_service] Erro ao ler tabela '%s': %s", table_name, exc
        )
        return None


# ---------------------------------------------------------------------------
# Escrita de DataFrame em tabela
# ---------------------------------------------------------------------------

def write_dataframe_to_table(
    df: pd.DataFrame,
    table_name: str,
    mode: str = "append",
) -> bool:
    """
    Escreve um DataFrame em uma tabela Snowflake via Snowpark.
    Retorna False se não estiver rodando no Snowflake ou se ocorrer erro.

    Parâmetros:
        df         — DataFrame a escrever
        table_name — nome qualificado da tabela (ex: "STAGING.forecast_normalized")
        mode       — "append" (padrão) | "overwrite"
                     "append"    → insere linhas sem truncar a tabela
                     "overwrite" → trunca a tabela antes de inserir

    Retorno:
        True se a escrita foi bem-sucedida | False caso contrário

    Exemplo:
        success = write_dataframe_to_table(
            staging_df,
            "STAGING.forecast_normalized",
            mode="append",
        )
        if not success:
            st.warning("Dados não foram persistidos — ambiente local.")
    """
    session = get_snowflake_session()
    if session is None:
        logger.debug(
            "[snowflake_service] write_dataframe_to_table(%s) ignorado — sem sessão.",
            table_name,
        )
        return False

    if df is None or df.empty:
        logger.warning(
            "[snowflake_service] write_dataframe_to_table(%s): DataFrame vazio.",
            table_name,
        )
        return False

    try:
        snowpark_df = session.create_dataframe(df)
        snowpark_df.write.mode(mode).save_as_table(table_name)
        logger.info(
            "[snowflake_service] %d linhas escritas em '%s' (mode=%s).",
            len(df), table_name, mode,
        )
        return True
    except Exception as exc:
        logger.error(
            "[snowflake_service] Erro ao escrever em '%s': %s", table_name, exc
        )
        return False


# ---------------------------------------------------------------------------
# Utilitário de diagnóstico
# ---------------------------------------------------------------------------

def get_connection_info() -> dict:
    """
    Retorna um dict com informações do ambiente de execução.
    Útil para diagnóstico em telas administrativas.

    Retorno:
        {
            "is_snowflake": bool,
            "current_user": str | None,
            "current_database": str | None,
            "current_schema": str | None,
            "current_warehouse": str | None,
        }
    """
    info = {
        "is_snowflake":       False,
        "current_user":       None,
        "current_database":   None,
        "current_schema":     None,
        "current_warehouse":  None,
    }

    if not is_running_in_snowflake():
        return info

    info["is_snowflake"] = True

    try:
        session = get_snowflake_session()
        if session is None:
            return info

        row = session.sql(
            """
            SELECT
                CURRENT_USER()      AS current_user,
                CURRENT_DATABASE()  AS current_database,
                CURRENT_SCHEMA()    AS current_schema,
                CURRENT_WAREHOUSE() AS current_warehouse
            """
        ).collect()

        if row:
            r = row[0]
            info["current_user"]      = r["CURRENT_USER"]
            info["current_database"]  = r["CURRENT_DATABASE"]
            info["current_schema"]    = r["CURRENT_SCHEMA"]
            info["current_warehouse"] = r["CURRENT_WAREHOUSE"]

    except Exception as exc:
        logger.warning(
            "[snowflake_service] Falha ao obter informações de conexão: %s", exc
        )

    return info
