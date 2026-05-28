"""
supplier_upload.py

Tela de upload de arquivo de forecast pelo fornecedor.
Permite baixar o template oficial, selecionar o arquivo .xlsx ou .csv,
acionar a validação explicitamente via botão e receber o resultado.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from components.cards import metric_card, render_cards_row
from components.tables import errors_table
from services.validation_service import ValidationResult, validate_forecast
from services.forecast_service import NormalizationResult, normalize_forecast
from services.upload_service import persist_upload_batch, persist_validation_errors, persist_validated_forecast
from utils.file_reader import normalize_columns, read_excel_file, read_uploaded_file, build_error_report
from utils.logger import get_logger
from utils.session_state import register_upload, register_validated_forecast
from utils.streamlit_compat import safe_rerun

_logger = get_logger(__name__)

# Caminhos oficiais dos templates
_TEMPLATE_PATH      = Path(__file__).parent.parent / "templates" / "template_forecast.xlsx"
_TEMPLATE_CSV_PATH  = Path(__file__).parent.parent / "templates" / "template_forecast.csv"

# Colunas esperadas no template (exibidas ao fornecedor)
_EXPECTED_COLUMNS: list[str] = [
    "Data_Envio",
    "Distribuidor_Nome",
    "Cidade_Filial",
    "NFMAT",
    "MATERIAL",
    "Descrição",
    "Ranking_Nacional",
    "Qtd",
    "Data_recebimento",
    "Observacoes",
]


# ---------------------------------------------------------------------------
# Seção 1 — Template
# ---------------------------------------------------------------------------

def _render_template_section() -> None:
    """Seção de download dos templates oficiais (XLSX e CSV)."""
    st.markdown(
        """
        <div class="kmt-section">
            <p class="kmt-section-title">Baixar template oficial</p>
            <p class="kmt-section-subtitle">
                Use o template abaixo como base para preencher os dados de forecast.
                Não altere os nomes das colunas.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    xlsx_exists = _TEMPLATE_PATH.exists() and _TEMPLATE_PATH.stat().st_size > 0
    csv_exists  = _TEMPLATE_CSV_PATH.exists() and _TEMPLATE_CSV_PATH.stat().st_size > 0

    if xlsx_exists or csv_exists:
        col_xlsx, col_csv, col_info, _ = st.columns([2, 2, 4, 1])

        with col_xlsx:
            if xlsx_exists:
                with open(_TEMPLATE_PATH, "rb") as f:
                    st.download_button(
                        label="⬇  Baixar Template XLSX",
                        data=f,
                        file_name="template_forecast.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            else:
                st.markdown(
                    """
                    <div class="kmt-alert kmt-alert--info" style="font-size:11px;padding:8px 12px;">
                        <p style="margin:0;">Template XLSX não encontrado.<br>
                        Entre em contato com a Komatsu.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with col_csv:
            if csv_exists:
                with open(_TEMPLATE_CSV_PATH, "rb") as f:
                    st.download_button(
                        label="⬇  Baixar Template CSV",
                        data=f,
                        file_name="template_forecast.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
            else:
                st.markdown(
                    """
                    <div class="kmt-alert kmt-alert--info" style="font-size:11px;padding:8px 12px;">
                        <p style="margin:0;">Template CSV não encontrado.<br>
                        Entre em contato com a Komatsu.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with col_info:
            st.markdown(
                """
                <div style="padding:10px 0 0 4px;font-size:12px;color:#9CA3AF;">
                    Preencha o template com os dados do período e envie abaixo.
                    Não altere os nomes das colunas.
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div class="kmt-alert kmt-alert--info">
                <div class="kmt-alert-icon">ℹ️</div>
                <div>
                    <p class="kmt-alert-title">Template oficial não encontrado</p>
                    <p class="kmt-alert-body">
                        Entre em contato com a Komatsu para validar o modelo de preenchimento.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Seção 2 — Colunas esperadas (exibidas como referência)
# ---------------------------------------------------------------------------

def _render_expected_columns() -> None:
    """Card com as colunas esperadas no arquivo de forecast."""
    mid = len(_EXPECTED_COLUMNS) // 2
    left  = _EXPECTED_COLUMNS[:mid]
    right = _EXPECTED_COLUMNS[mid:]

    left_html  = "".join(
        f'<div style="font-size:12px;color:#374151;padding:3px 0;">'
        f'<span style="color:#FFCD00;margin-right:6px;">▸</span>{col}</div>'
        for col in left
    )
    right_html = "".join(
        f'<div style="font-size:12px;color:#374151;padding:3px 0;">'
        f'<span style="color:#FFCD00;margin-right:6px;">▸</span>{col}</div>'
        for col in right
    )

    st.markdown(
        f"""
        <div class="kmt-card" style="margin-bottom:20px;">
            <p class="kmt-card-label" style="margin-bottom:12px;">Colunas esperadas</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px;">
                <div>{left_html}</div>
                <div>{right_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Área de upload de arquivo
# ---------------------------------------------------------------------------

def _render_upload_area() -> tuple[pd.DataFrame | None, str | None, str | None]:
    """
    Renderiza o file uploader e, se necessário, o seletor de aba.
    Retorna (DataFrame | None, nome_do_arquivo | None, erro | None).
    """
    uploaded = st.file_uploader(
        "Selecione o arquivo de forecast",
        type=["xlsx", "csv"],
        help="Formatos aceitos: .xlsx e .csv · Limite: 50 MB",
        label_visibility="collapsed",
    )

    if uploaded is None:
        return None, None, None

    file_name = uploaded.name

    if file_name.lower().endswith(".csv"):
        df, err = read_uploaded_file(uploaded)
        return df, file_name, err

    # XLSX: oferece seleção de aba se houver mais de uma
    df, sheet_names, err = read_excel_file(uploaded, sheet_name=0)

    if err:
        return None, file_name, err

    if len(sheet_names) > 1:
        st.markdown(
            '<p style="font-size:12px;font-weight:700;color:#9CA3AF;'
            'text-transform:uppercase;letter-spacing:0.1em;margin:12px 0 4px;">Aba do arquivo</p>',
            unsafe_allow_html=True,
        )
        selected = st.selectbox(
            "Selecione a aba:",
            options=sheet_names,
            index=0,
            label_visibility="collapsed",
        )
        if selected != sheet_names[0]:
            uploaded.seek(0)
            df, _, err = read_excel_file(uploaded, sheet_name=selected)

    return df, file_name, err


# ---------------------------------------------------------------------------
# Prompt de arquivo pronto (antes da validação)
# ---------------------------------------------------------------------------

def _render_file_ready_prompt(file_name: str, n_rows: int) -> None:
    """Exibe informações do arquivo selecionado e o botão de validação."""
    st.markdown(
        f"""
        <div class="kmt-alert kmt-alert--info" style="margin-top:12px;">
            <div class="kmt-alert-icon">📄</div>
            <div>
                <p class="kmt-alert-title">Arquivo selecionado</p>
                <p class="kmt-alert-body">
                    <strong>{file_name}</strong> · {n_rows} linha(s) detectada(s).
                    Clique em <strong>Validar arquivo</strong> para iniciar a verificação.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    col_btn, _ = st.columns([2, 4])
    with col_btn:
        if st.button("✔  Validar arquivo", key="btn_validate", use_container_width=True):
            st.session_state.upload_validate_pending = True
            safe_rerun()


# ---------------------------------------------------------------------------
# Seção 3 — Resultado de sucesso (visão fornecedor)
# ---------------------------------------------------------------------------

def _render_success_supplier(result: ValidationResult) -> None:
    """Resultado quando o arquivo é válido — sem termos técnicos internos."""
    st.markdown(
        """
        <div class="kmt-alert kmt-alert--success">
            <div class="kmt-alert-icon">✅</div>
            <div>
                <p class="kmt-alert-title">Arquivo válido para processamento.</p>
                <p class="kmt-alert-body">
                    Todas as validações foram aprovadas.
                    O envio foi registrado e está disponível no histórico.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total   = result.summary["total_rows"]
    valid   = result.summary["valid_rows"]
    invalid = result.summary["invalid_rows"]

    render_cards_row([
        metric_card("Total de Linhas",  str(total)),
        metric_card("Linhas Válidas",   str(valid)),
        metric_card("Linhas com Erro",  str(invalid)),
        metric_card("Status do Envio",  "Válido"),
    ])

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    col_hist, _ = st.columns([2, 4])
    with col_hist:
        if st.button("📋  Ver Meus Envios", key="success_btn_history", use_container_width=True):
            st.session_state.page = "history"
            safe_rerun()


# ---------------------------------------------------------------------------
# Seção 3 — Resultado de erros (visão fornecedor)
# ---------------------------------------------------------------------------

def _render_errors_supplier(result: ValidationResult, file_name: str) -> None:
    """Resultado quando o arquivo tem erros — sem termos técnicos internos."""
    n_errors = len(result.errors_dataframe)

    st.markdown(
        f"""
        <div class="kmt-alert kmt-alert--error">
            <div class="kmt-alert-icon">❌</div>
            <div>
                <p class="kmt-alert-title">
                    Arquivo inválido — {n_errors} erro(s) encontrado(s)
                </p>
                <p class="kmt-alert-body">
                    Corrija os erros listados abaixo no arquivo original e reenvie.
                    Não é possível editar os dados diretamente no portal.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_cards_row([
        metric_card("Total de Linhas",   str(result.summary["total_rows"])),
        metric_card("Linhas com Erro",   str(result.summary["invalid_rows"])),
        metric_card("Erros Encontrados", str(n_errors)),
    ])

    st.markdown('<div class="kmt-spacer-md"></div>', unsafe_allow_html=True)

    st.markdown(errors_table(result.errors_dataframe), unsafe_allow_html=True)

    st.markdown('<div class="kmt-spacer-sm"></div>', unsafe_allow_html=True)

    col_dl, col_hist, _ = st.columns([2, 2, 2])
    with col_dl:
        report_name_base = file_name.rsplit(".", 1)[0]
        report_data, report_file, report_mime = build_error_report(
            result.errors_dataframe, report_name_base
        )
        st.download_button(
            label="⬇  Baixar relatório de correção",
            data=report_data,
            file_name=report_file,
            mime=report_mime,
            use_container_width=True,
        )
    with col_hist:
        if st.button("📋  Ver Meus Envios", key="error_btn_history", use_container_width=True):
            st.session_state.page = "history"
            safe_rerun()


# ---------------------------------------------------------------------------
# Extração de período (utilitário interno)
# ---------------------------------------------------------------------------

def _extract_period_from_df(df: pd.DataFrame) -> str:
    """
    Tenta extrair o período AAAA-MM da coluna de data do arquivo.
    Retorna "—" se não for possível determinar o período.
    """
    col_map = normalize_columns(df)
    date_col = col_map.get("data_recebimento")
    if not date_col:
        return "—"
    try:
        dates = df[date_col].dropna()
        if dates.empty:
            return "—"
        parsed = pd.to_datetime(dates.iloc[0], dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return "—"
        return parsed.strftime("%Y-%m")
    except Exception:
        return "—"


# ---------------------------------------------------------------------------
# Sincronização do fornecedor após upload (BUG-03 / BUG-04)
# ---------------------------------------------------------------------------

def _sync_supplier_after_upload(supplier_id: str) -> None:
    """
    Atualiza period_status e last_upload do fornecedor na sessão após upload.

    Espelha a lógica de get_admin_status_rows() para garantir que a tabela
    de Gestão de Fornecedores reflita o estado real dos uploads da sessão:
    - Upload ativo e válido presente → period_status = "valid"
    - Sem upload válido, mas com inválido → period_status = "invalid"
    - Sem nenhum upload → permanece "pending"

    Deve ser chamada apenas dentro do bloco `if not already_registered:`,
    após register_upload() e register_validated_forecast() quando aplicável.
    """
    from utils.session_state import get_session_uploads, set_session_supplier

    sup_ups = get_session_uploads(supplier_id)
    if not sup_ups:
        return

    # Prioridade: upload ativo e válido; caso contrário, o mais recente
    active_valid = next(
        (u for u in sup_ups if u.get("is_active") and u.get("status") == "valid"),
        None,
    )
    ref = active_valid or sup_ups[0]

    set_session_supplier(supplier_id, {
        "period_status": ref.get("status", "pending"),
        "last_upload":   ref.get("sent_at", "—"),
    })


# ---------------------------------------------------------------------------
# Ponto de entrada da tela
# ---------------------------------------------------------------------------

def render() -> None:
    """
    Renderiza a tela de upload de forecast em 3 seções:
      1. Baixar template oficial
      2. Enviar arquivo de forecast (com colunas esperadas)
      3. Resultado da validação (somente após clicar "Validar arquivo")

    Chamado por streamlit_app.py quando page == 'upload'.
    """
    # --- Seção 1: Template ---------------------------------------------------
    _render_template_section()

    st.markdown('<div class="kmt-divider"></div>', unsafe_allow_html=True)

    # --- Seção 2: Upload -----------------------------------------------------
    st.markdown(
        """
        <div class="kmt-section" style="margin-top:8px;">
            <p class="kmt-section-title">Enviar arquivo de forecast</p>
            <p class="kmt-section-subtitle">
                Selecione um arquivo <strong>.xlsx</strong> ou <strong>.csv</strong>
                preenchido com o template oficial.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_upload, col_check = st.columns([3, 2])

    with col_upload:
        st.markdown(
            '<div class="kmt-card" style="margin-bottom:16px;">'
            '<p class="kmt-card-label" style="margin-bottom:12px;">Arquivo de Forecast</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        df, file_name, read_error = _render_upload_area()

    with col_check:
        _render_expected_columns()

    # --- Erro de leitura -----------------------------------------------------
    if df is None and read_error:
        st.markdown(
            f"""
            <div class="kmt-alert kmt-alert--error">
                <div class="kmt-alert-icon">⚠</div>
                <div>
                    <p class="kmt-alert-title">Erro ao ler o arquivo</p>
                    <p class="kmt-alert-body">{read_error}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if df is None:
        return

    # --- Máquina de estados: validação explícita por botão ------------------
    # file_key inclui supplier_id para garantir que o mesmo arquivo enviado
    # por fornecedores diferentes em uma mesma sessão não acione a deduplicação
    # indevidamente (already_registered = True) e bloqueie o registro do upload.
    _sid     = (st.session_state.get("supplier_id") or "").upper()
    file_key = f"{_sid}_{file_name}_{len(df)}"

    # Arquivo mudou → reseta estado de validação
    if st.session_state.get("upload_current_file_key") != file_key:
        st.session_state.upload_validate_pending = False
        st.session_state.upload_current_file_key = file_key

    if not st.session_state.get("upload_validate_pending", False):
        _render_file_ready_prompt(file_name, len(df))
        return

    # --- Seção 3: Resultado --------------------------------------------------
    st.markdown('<div class="kmt-divider"></div>', unsafe_allow_html=True)

    supplier_name  = st.session_state.get("user_name", "")
    supplier_id    = st.session_state.get("supplier_id") or ""
    # uploaded_by: e-mail do fornecedor logado no momento do envio.
    # Usar supplier_email (definido no login) e não user_email, que pode
    # mudar se admin visualizar depois o detalhe.
    supplier_email = (
        st.session_state.get("supplier_email")
        or st.session_state.get("user_email")
        or "—"
    )

    # Deduplicação: só registra uma vez por arquivo por sessão
    already_registered = st.session_state.get("last_processed_file") == file_key

    with st.spinner("Validando arquivo..."):
        result = validate_forecast(df, supplier_name=supplier_name)

    if result.is_valid:
        _logger.info(
            "Validação OK: supplier=%s, file=%s, rows=%d",
            supplier_id, file_name, result.summary.get("total_rows", 0),
        )
        # Normalização para extrair período e obter staging_dataframe
        norm_result = normalize_forecast(
            normalized_df=result.normalized_dataframe,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            upload_id="PREVIEW",
            upload_version=1,
            source_file_name=file_name,
        )
        periods    = norm_result.summary.get("periods", [])
        period_raw = periods[0] if periods else "—"
        # Normalizar para YYYY-MM — get_admin_status_rows() compara neste formato.
        # Sem isso, datas no formato "2026-05-01" não casam com o período "2026-05"
        # da janela aberta e o fornecedor fica sempre como pendente no painel.
        if period_raw != "—":
            try:
                _p = pd.to_datetime(period_raw, dayfirst=True, errors="coerce")
                period = _p.strftime("%Y-%m") if not pd.isna(_p) else period_raw
            except Exception:
                period = period_raw
        else:
            period = period_raw
        report_type = "Forecast DB"

        if not already_registered:
            # Persistir no Snowflake primeiro — fonte de verdade
            sf_result = persist_upload_batch(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                user_id=st.session_state.get("user_id") or supplier_id,
                file_name=file_name,
                reference_period=period,
                status="valid",
                valid_rows=result.summary["total_rows"],
                invalid_rows=0,
                uploaded_by=supplier_email,
                report_type=report_type,
            )
            if sf_result is None:
                st.error(
                    "Falha ao registrar upload no Snowflake. "
                    "O arquivo não foi persistido. Tente novamente."
                )
                return
            sf_upload_id = sf_result["upload_id"]
            sf_version = sf_result["version"]

            # Registrar em session_state (temporário — leitura ainda depende disso)
            upload_id_final = register_upload(
                file_name=     file_name,
                supplier_id=   supplier_id,
                supplier_name= supplier_name,
                period=        period,
                status=        "valid",
                valid_rows=    result.summary["total_rows"],
                invalid_rows=  0,
                report_type=   report_type,
                uploaded_by=   supplier_email,
            )
            # Sobrescrever o upload_id local com o UUID do Snowflake
            # para manter consistência entre session_state e banco
            for rec in st.session_state.get("session_uploads", []):
                if rec.get("upload_id") == upload_id_final:
                    rec["upload_id"] = sf_upload_id
                    break
            upload_id_final = sf_upload_id

            st.session_state.last_processed_file = file_key

            # Salvar linhas normalizadas com o upload_id real
            from utils.session_state import get_session_upload_by_id
            staging_df = norm_result.staging_dataframe.copy()
            staging_df["upload_id"] = upload_id_final
            upload_rec = get_session_upload_by_id(upload_id_final)
            if upload_rec:
                staging_df["upload_version"] = upload_rec["version"]

            # Persistir linhas válidas em TRUSTED.FORECAST_VALIDATED (Snowflake)
            # Usa sf_version (versão real do Snowflake) — não a versão do session_state
            staging_df["upload_version"] = sf_version
            trusted_count = persist_validated_forecast(
                upload_id=upload_id_final,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                upload_version=sf_version,
                source_file_name=file_name,
                staging_df=staging_df,
            )
            if trusted_count == 0 and len(staging_df) > 0:
                st.error(
                    "Falha ao persistir dados validados no Snowflake. "
                    "O upload foi registrado mas as linhas não foram salvas."
                )
                return

            _logger.info(
                "Forecast validado persistido: upload_id=%s, linhas=%d",
                upload_id_final, trusted_count,
            )

            # session_state (temporário — tela de Forecasts Validados ainda lê daqui)
            register_validated_forecast(upload_id_final, staging_df)
            _sync_supplier_after_upload(supplier_id)

        _render_success_supplier(result)

    else:
        _logger.info(
            "Validação FALHOU: supplier=%s, file=%s, erros=%d",
            supplier_id, file_name, len(result.errors_dataframe),
        )
        if not already_registered:
            period      = _extract_period_from_df(df)
            report_type = "Forecast DB"
            errors_list = result.errors_dataframe.to_dict("records")

            # Persistir upload inválido no Snowflake
            sf_result = persist_upload_batch(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                user_id=st.session_state.get("user_id") or supplier_id,
                file_name=file_name,
                reference_period=period,
                status="invalid",
                valid_rows=0,
                invalid_rows=len(result.errors_dataframe),
                uploaded_by=supplier_email,
                report_type=report_type,
            )
            if sf_result is None:
                st.error(
                    "Falha ao registrar upload no Snowflake. "
                    "O arquivo não foi persistido. Tente novamente."
                )
                return
            sf_upload_id = sf_result["upload_id"]

            # Persistir erros de validação no Snowflake
            errors_persisted = persist_validation_errors(
                upload_id=sf_upload_id,
                errors=errors_list,
            )
            if errors_persisted == 0 and len(errors_list) > 0:
                st.error(
                    "Falha ao registrar erros de validação no Snowflake. "
                    "O upload foi registrado mas os erros não foram persistidos."
                )
                return

            _logger.info(
                "Erros de validação persistidos: upload_id=%s, erros=%d",
                sf_upload_id, errors_persisted,
            )

            # Registrar em session_state (temporário — tela de erros ainda lê daqui)
            upload_id_local = register_upload(
                file_name=     file_name,
                supplier_id=   supplier_id,
                supplier_name= supplier_name,
                period=        period,
                status=        "invalid",
                valid_rows=    0,
                invalid_rows=  len(result.errors_dataframe),
                report_type=   report_type,
                errors=        errors_list,
                uploaded_by=   supplier_email,
            )
            # Sobrescrever o upload_id local com o UUID do Snowflake
            for rec in st.session_state.get("session_uploads", []):
                if rec.get("upload_id") == upload_id_local:
                    rec["upload_id"] = sf_upload_id
                    break
            # Atualizar chave dos erros
            errs = st.session_state.get("session_errors", {})
            if upload_id_local in errs:
                errs[sf_upload_id] = errs.pop(upload_id_local)

            st.session_state.last_processed_file = file_key
            _sync_supplier_after_upload(supplier_id)

        _render_errors_supplier(result, file_name)
