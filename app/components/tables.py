"""
tables.py

Componente de tabelas reutilizáveis.
Formata e exibe DataFrames com estilo padronizado Komatsu,
aplicando filtros, paginação simples e destaque por status.
"""

import html as _html

import pandas as pd
import streamlit as st
from components.badges import status_badge, version_badge
from services.mock_data_service import get_mock_uploads, get_admin_table_rows


def demo_history_table(title: str = "Rastreabilidade de Arquivos") -> str:
    """
    Retorna HTML da tabela de histórico de envios com dados de mock_data_service.
    Exibe os uploads de Vianmaq (SUP001) — tela do fornecedor.
    Uso: st.markdown(demo_history_table(), unsafe_allow_html=True)
    """
    shipments = get_mock_uploads(supplier_id="SUP001")
    rows = ""
    for s in shipments:
        badge = status_badge(s["status"])
        ver   = version_badge(s["version"])
        rows += f"""
        <tr class="kmt-table-row">
            <td class="kmt-table-cell kmt-td-id">{s['upload_id']}</td>
            <td class="kmt-table-cell">{s['file_name']}</td>
            <td class="kmt-table-cell kmt-td-period">{s['period']}</td>
            <td class="kmt-table-cell kmt-td-center">{ver}</td>
            <td class="kmt-table-cell">{badge}</td>
            <td class="kmt-table-cell kmt-td-date">{s['sent_at']}</td>
        </tr>"""

    return f"""
    <div class="kmt-table-container">
        <div class="kmt-table-header">
            <span class="kmt-table-title">{title}</span>
        </div>
        <div class="kmt-table-scroll">
            <table class="kmt-table">
                <thead>
                    <tr class="kmt-thead-row">
                        <th class="kmt-th">Upload ID</th>
                        <th class="kmt-th">Arquivo</th>
                        <th class="kmt-th">Período</th>
                        <th class="kmt-th kmt-th-center">Versão</th>
                        <th class="kmt-th">Status</th>
                        <th class="kmt-th">Data Envio</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>"""


def demo_admin_table(title: str = "Status por Fornecedor") -> str:
    """
    Retorna HTML da tabela administrativa de fornecedores com dados de mock_data_service.
    Uso: st.markdown(demo_admin_table(), unsafe_allow_html=True)
    """
    admin_rows = get_admin_table_rows()

    rows = ""
    for r in admin_rows:
        badge  = status_badge(r["status"])
        errors = r["errors"]
        errors_html = (
            f'<span style="color:#EF4444;font-weight:700;">{errors}</span>'
            if isinstance(errors, int) and errors > 0
            else f'<span style="color:#E5E7EB;">—</span>'
        )
        rows += f"""
        <tr class="kmt-table-row">
            <td class="kmt-table-cell" style="font-weight:700;color:#002B5C;">{r['name']}</td>
            <td class="kmt-table-cell kmt-td-period">{r['period']}</td>
            <td class="kmt-table-cell">{badge}</td>
            <td class="kmt-table-cell kmt-td-date">{r['last']}</td>
            <td class="kmt-table-cell kmt-td-center" style="font-family:monospace;font-weight:700;color:#9CA3AF;">{r['version']}</td>
            <td class="kmt-table-cell kmt-td-center">{errors_html}</td>
        </tr>"""

    return f"""
    <div class="kmt-table-container">
        <div class="kmt-table-header">
            <span class="kmt-table-title">{title}</span>
        </div>
        <div class="kmt-table-scroll">
            <table class="kmt-table">
                <thead>
                    <tr class="kmt-thead-row">
                        <th class="kmt-th">Fornecedor</th>
                        <th class="kmt-th">Período</th>
                        <th class="kmt-th">Status</th>
                        <th class="kmt-th">Último Envio</th>
                        <th class="kmt-th kmt-th-center">Versão</th>
                        <th class="kmt-th kmt-th-center">Erros</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>"""


def errors_table(
    errors_df: pd.DataFrame,
    title: str = "Detalhamento das Inconsistências",
) -> str:
    """
    Retorna HTML da tabela de erros de validação.
    Colunas esperadas no DataFrame (snake_case):
        linha, coluna, valor_informado, erro, orientacao_correcao
    Uso: st.markdown(errors_table(df), unsafe_allow_html=True)
    """
    if errors_df.empty:
        return ""

    rows = ""
    for _, row in errors_df.iterrows():
        linha_raw  = row["linha"]
        linha_val  = int(linha_raw) if linha_raw != 0 else "—"
        # Linha 0 indica erro de estrutura (coluna ausente), estilo diferenciado
        linha_style = (
            'style="font-family:monospace;font-weight:700;color:#002B5C;"'
            if linha_raw != 0
            else 'style="font-family:monospace;font-weight:700;color:#9CA3AF;"'
        )
        valor_safe = _html.escape(str(row["valor_informado"]))
        erro_safe  = _html.escape(str(row["erro"]))
        col_safe   = _html.escape(str(row["coluna"]))
        ori_safe   = _html.escape(str(row["orientacao_correcao"]))

        valor_html = (
            f'<span style="padding:2px 8px;background:#F3F4F6;'
            f'border:1px solid #E5E7EB;border-radius:4px;font-size:11px;">'
            f"{valor_safe}</span>"
        )
        rows += f"""
        <tr class="kmt-table-row">
            <td class="kmt-table-cell" {linha_style}>{linha_val}</td>
            <td class="kmt-table-cell" style="font-weight:600;">{col_safe}</td>
            <td class="kmt-table-cell">{valor_html}</td>
            <td class="kmt-table-cell" style="color:#B91C1C;font-weight:500;">{erro_safe}</td>
            <td class="kmt-table-cell" style="color:#6B7280;font-style:italic;font-size:11px;text-transform:uppercase;">{ori_safe}</td>
        </tr>"""

    return f"""
    <div class="kmt-table-container">
        <div class="kmt-table-header">
            <span class="kmt-table-title">{_html.escape(title)}</span>
        </div>
        <div class="kmt-table-scroll">
            <table class="kmt-table">
                <thead>
                    <tr class="kmt-thead-row">
                        <th class="kmt-th">Linha</th>
                        <th class="kmt-th">Coluna</th>
                        <th class="kmt-th">Valor Informado</th>
                        <th class="kmt-th">Erro Detectado</th>
                        <th class="kmt-th">Orientação</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>"""


def preview_table(
    df: pd.DataFrame,
    n: int = 5,
    title: str = "Prévia do Arquivo",
) -> str:
    """
    Retorna HTML das primeiras n linhas de um DataFrame com estilo Komatsu.
    Usa os nomes reais das colunas do arquivo (não os canônicos).
    Uso: st.markdown(preview_table(df), unsafe_allow_html=True)
    """
    preview = df.head(n)
    cols = list(preview.columns)

    header_cells = "".join(
        f'<th class="kmt-th">{_html.escape(str(c))}</th>' for c in cols
    )

    rows = ""
    for _, row in preview.iterrows():
        cells = ""
        for c in cols:
            val = str(row[c]) if not pd.isna(row[c]) else ""
            # Truncar valores muito longos
            val_display = val[:45] + "…" if len(val) > 45 else val
            cells += f'<td class="kmt-table-cell">{_html.escape(val_display)}</td>'
        rows += f'<tr class="kmt-table-row">{cells}</tr>'

    return f"""
    <div class="kmt-table-container">
        <div class="kmt-table-header">
            <span class="kmt-table-title">{_html.escape(title)}</span>
            <span style="font-size:11px;color:#9CA3AF;">
                Exibindo {len(preview)} de {len(df)} linha(s)
            </span>
        </div>
        <div class="kmt-table-scroll">
            <table class="kmt-table">
                <thead>
                    <tr class="kmt-thead-row">{header_cells}</tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>"""
