"""
dates.py

Funções utilitárias de data e período.
Responsável por calcular ciclos de coleta, formatar datas para exibição,
validar janelas de envio e cancelamento e converter períodos de forecast.
"""

_MONTHS_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",    6: "Junho",    7: "Julho",     8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def format_period_pt(period_str: str) -> str:
    """
    Converte um período de forecast para formato amigável em português.

    Aceita:
      - "YYYY-MM-DD" → "Mês/YYYY"  (ex.: 2026-05-01 → Maio/2026)
      - "YYYY-MM"    → "Mês/YYYY"  (ex.: 2026-05    → Maio/2026)

    Valores não reconhecidos são retornados sem alteração.
    """
    if not period_str or period_str == "—":
        return period_str

    parts = period_str.split("-")
    if len(parts) >= 2:
        try:
            year  = int(parts[0])
            month = int(parts[1])
            if 1 <= month <= 12 and 1900 <= year <= 2100:
                return f"{_MONTHS_PT[month]}/{year}"
        except (ValueError, IndexError):
            pass

    return period_str


def to_period_ym(period_str: str) -> str:
    """
    Normaliza qualquer representação de período para o formato YYYY-MM.

    Aceita:
      - "YYYY-MM"             → "2026-05"  (já correto)
      - "YYYY-MM-DD"          → "2026-05"  (trunca o dia)
      - "YYYY-MM-DD HH:MM:SS" → "2026-05"  (trunca dia + hora)
      - "DD/MM/YYYY"          → "2026-05"  (parse com dayfirst=True)
      - Qualquer formato aceito por pd.to_datetime com dayfirst=True.

    Retorna "" para entradas vazias, "—", "nan" ou não reconhecidas.

    Usado por get_admin_status_rows() e _get_available_periods() para garantir
    que períodos em formatos diferentes sejam comparados corretamente com
    o formato canônico "YYYY-MM" da janela de envio.
    """
    if not period_str or period_str in ("—", "nan", ""):
        return ""

    # YYYY-MM ou YYYY-MM-... (inclui datas completas e timestamps)
    if len(period_str) >= 7 and period_str[4:5] == "-":
        try:
            year  = int(period_str[:4])
            month = int(period_str[5:7])
            if 1900 <= year <= 2100 and 1 <= month <= 12:
                return f"{year}-{month:02d}"
        except (ValueError, IndexError):
            pass

    # Outros formatos (DD/MM/YYYY etc.) — tentar parse com pandas
    try:
        import pandas as _pd
        _p = _pd.to_datetime(period_str, dayfirst=True, errors="coerce")
        if not _pd.isna(_p):
            return _p.strftime("%Y-%m")
    except Exception:
        pass

    return ""
