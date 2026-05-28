"""
snowflake_service.py

Camada de abstração para acesso ao Snowflake.
Compatível com execução local e com Streamlit in Snowflake.

Comportamento por ambiente:
  - Streamlit in Snowflake  → usa get_active_session() do Snowpark (sem credenciais)
  - Execução local           → cria sessão via Snowpark Session.builder usando
                               connection_name da configuração ~/.snowflake/connections.toml

Regras:
  - Sem credenciais no código.
  - Falha controlada: nenhuma exceção propaga para a UI.
"""

import os
from typing import Optional

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

# Cache da sessão local para evitar reconexões a cada chamada
_local_session_cache = None

# Nome da conexão usada localmente (connections.toml)
_LOCAL_CONNECTION_NAME = os.environ.get(
    "SNOWFLAKE_CONNECTION_NAME", "KOMATSU_BRAZIL_INTERNATIONAL_PAT"
)


# ---------------------------------------------------------------------------
# Detecção de ambiente
# ---------------------------------------------------------------------------

def is_running_in_snowflake() -> bool:
    """
    Retorna True se o app está rodando dentro do Streamlit in Snowflake.
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
    Retorna uma sessão Snowpark.

    Prioridade:
      1. Streamlit in Snowflake (get_active_session)
      2. Conexão local via Session.builder (connections.toml)

    Retorno:
        snowflake.snowpark.Session | None
    """
    global _local_session_cache

    # 1. Tentar SiS
    try:
        from snowflake.snowpark.context import get_active_session
        session = get_active_session()
        if session is not None:
            return session
    except Exception:
        pass

    # 2. Tentar sessão local cacheada
    if _local_session_cache is not None:
        try:
            # Verifica se a sessão ainda está válida
            _local_session_cache.sql("SELECT 1").collect()
            return _local_session_cache
        except Exception:
            _local_session_cache = None

    # 3. Criar sessão local via connections.toml
    try:
        from snowflake.snowpark import Session
        _local_session_cache = Session.builder.config(
            "connection_name", _LOCAL_CONNECTION_NAME
        ).create()
        logger.info(
            "Sessão local criada via conexão '%s'.",
            _LOCAL_CONNECTION_NAME,
        )
        return _local_session_cache
    except Exception as exc:
        logger.error(
            "FALHA ao criar sessão local.\n"
            "  connection_name: %s\n"
            "  config_file: ~/.snowflake/connections.toml\n"
            "  erro: %s\n"
            "  tipo: %s\n"
            "  Possíveis causas:\n"
            "    - Conexão '%s' não existe em connections.toml\n"
            "    - Credencial expirada ou inválida (token/password)\n"
            "    - Account name incorreto\n"
            "    - Rede/firewall bloqueando acesso ao Snowflake\n"
            "    - snowflake-snowpark-python não instalado",
            _LOCAL_CONNECTION_NAME, exc, type(exc).__name__,
            _LOCAL_CONNECTION_NAME,
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
            "Falha ao obter usuário Snowflake: %s", exc
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
            "execute_query ignorado — sem sessão Snowflake."
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
            "Erro ao executar query: %s\nQuery: %s",
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
            "read_table(%s) ignorado — sem sessão Snowflake.",
            table_name,
        )
        return None

    limit_clause = f" LIMIT {int(limit)}" if limit else ""
    query = f"SELECT * FROM {table_name}{limit_clause}"

    try:
        return session.sql(query).to_pandas()
    except Exception as exc:
        logger.error(
            "Erro ao ler tabela '%s': %s", table_name, exc
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
            "write_dataframe_to_table(%s) ignorado — sem sessão.",
            table_name,
        )
        return False

    if df is None or df.empty:
        logger.warning(
            "write_dataframe_to_table(%s): DataFrame vazio.",
            table_name,
        )
        return False

    try:
        snowpark_df = session.create_dataframe(df)
        snowpark_df.write.mode(mode).save_as_table(table_name)
        logger.info(
            "%d linhas escritas em '%s' (mode=%s).",
            len(df), table_name, mode,
        )
        return True
    except Exception as exc:
        logger.error(
            "Erro ao escrever em '%s': %s", table_name, exc
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

    session = get_snowflake_session()
    if session is None:
        return info

    info["is_snowflake"] = True

    try:

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
            "Falha ao obter informações de conexão: %s", exc
        )

    return info
