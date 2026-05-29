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
