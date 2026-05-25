"""
badges.py

Componente de badges de status.
Renderiza rótulos visuais coloridos para representar estados dos envios:
Ex: Pendente, Enviado, Validado, Rejeitado, Cancelado.
"""

# Configuração de cores e labels por status
_STATUS_CONFIG: dict[str, dict] = {
    # Status de upload
    "valid":        {"bg": "#DCFCE7", "color": "#15803D", "label": "Válido/Ativo"},
    "invalid":      {"bg": "#FEE2E2", "color": "#B91C1C", "label": "Inválido"},
    "replaced":     {"bg": "#DBEAFE", "color": "#1D4ED8", "label": "Substituído"},
    "canceled":     {"bg": "#F3F4F6", "color": "#374151", "label": "Cancelado"},
    "processed":    {"bg": "rgba(0,43,92,0.1)", "color": "#002B5C", "label": "Processado"},
    "pending":      {"bg": "#FEF9C3", "color": "#854D0E", "label": "Pendente"},
    # Status de fornecedor
    "active":       {"bg": "#DCFCE7", "color": "#15803D", "label": "Ativo"},
    "inactive":     {"bg": "#F3F4F6", "color": "#6B7280", "label": "Inativo"},
    "not_expected": {"bg": "#F3F4F6", "color": "#9CA3AF", "label": "Não esperado"},
}


def status_badge(status: str) -> str:
    """
    Retorna HTML de um badge de status com cor e label corretos.
    Uso: st.markdown(status_badge("valid"), unsafe_allow_html=True)
    """
    cfg = _STATUS_CONFIG.get(status, _STATUS_CONFIG["pending"])
    return (
        f'<span style="'
        f'display:inline-block;'
        f'padding:3px 10px;'
        f'border-radius:9999px;'
        f'font-size:11px;'
        f'font-weight:600;'
        f'background:{cfg["bg"]};'
        f'color:{cfg["color"]};'
        f'white-space:nowrap;'
        f'">{cfg["label"]}</span>'
    )


def version_badge(n: int | str) -> str:
    """
    Retorna HTML de um badge de versão (número em quadrado cinza).
    Uso: st.markdown(version_badge(2), unsafe_allow_html=True)
    """
    return (
        f'<span style="'
        f'display:inline-flex;'
        f'width:24px;height:24px;'
        f'align-items:center;justify-content:center;'
        f'background:#F3F4F6;'
        f'border-radius:4px;'
        f'font-size:11px;font-weight:700;'
        f'color:#374151;'
        f'">{n}</span>'
    )
