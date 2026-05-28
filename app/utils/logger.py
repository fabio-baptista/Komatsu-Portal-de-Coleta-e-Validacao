"""
logger.py

Logging centralizado do Portal Komatsu.
Configura handlers para stdout (sempre) e arquivo local (apenas em dev/test/local).

Uso:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("mensagem")

Variáveis de ambiente:
    LOG_LEVEL — nível de log (DEBUG, INFO, WARNING, ERROR). Default: INFO.
    APP_ENV   — ambiente (dev, test, local, production). Arquivo só em dev/test/local.

Segurança:
    - Nunca logar credenciais, tokens, senhas ou conteúdo de arquivos.
    - Em Streamlit in Snowflake, apenas stdout funciona (sem filesystem).
"""

import logging
import os
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
_APP_ENV = os.environ.get("APP_ENV", "dev")

_configured = False


def _configure_root() -> None:
    """Configura o root logger uma única vez."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))

    # Handler stdout (funciona em qualquer ambiente)
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in root.handlers):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(stdout_handler)

    # Handler arquivo local (apenas em dev/test/local, falha silenciosa)
    if _APP_ENV in ("dev", "test", "local"):
        try:
            from pathlib import Path
            log_dir = Path(__file__).parent.parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "app.log"
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
            root.addHandler(file_handler)
        except Exception:
            # Filesystem indisponível (ex: Streamlit in Snowflake) — ignorar
            pass


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado para o módulo informado.

    Parâmetro:
        name — tipicamente __name__ do módulo chamador.

    Retorno:
        logging.Logger configurado com handlers de stdout e arquivo (se aplicável).
    """
    _configure_root()
    return logging.getLogger(name)
