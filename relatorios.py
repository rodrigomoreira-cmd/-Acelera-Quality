import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
from database import get_all_records_db, supabase


def render_relatorios():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados. Verifique suas credenciais.")
        return
    # ------------------------------------------------------------------

    # 🎨 PALETA DE CORES SISTÊMICA
    COR_PRINCIPAL = "#FF7A00"  # Laranja vibrante principal
    COR_SUCESSO = "#00E676"
    COR_TEXTO = "#A0AEC0"
    COR_FUNDO_GRAFICO = "rgba(0,0,0,0)"

    st.markdown(
        f"<h1 style='color: {COR_PRINCIPAL};'>📊 Relatório Executivo (BI)</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Acompanhe os KPIs da equipe, tendências de notas e exporte a base consolidada para apresentações."
    )

    # 1. Recupera contexto de acesso
    nivel = str(st.session_state.get("nivel", "USUARIO"))
    dept_logado = str(st.session_state.get("departamento_selecionado", "Todos"))

    # 2. Busca os dados brutos
    df_mon = get_all_records_db("monitorias")
    df_cont = get_all_records_db("contestacoes")
    df_comp = get_all_records_db("avaliacoes_comportamentais")

    if df_mon is None or df_mon.empty:
        st.warning("Não há dados de monitoria suficientes para gerar relatórios.")
        return

    # =========================================================
    # 🛡️ TRAVAS DE SEGURANÇA E VISIBILIDADE
    # =========================================================
    # Oculta o Admin Mestre para não-admins
    if nivel != "ADMIN":
        df_mon = df_mon[
            (
                ~df_mon["sdr"]
                .astype(str)
                .str.contains("admin@grupoacelerador.com.br", na=False, case=False)
            )
            & (
                ~df_mon["monitor_responsavel"]
                .astype(str)
                .str.contains("admin@grupoacelerador.com.br", na=False, case=False)
            )
        ].copy()

        if df_comp is not None and not df_comp.empty:
            df_comp = df_comp[
                ~df_comp["sdr_nome"]
                .astype(str)
                .str.contains("admin@grupoacelerador.com.br", na=False, case=False)
            ].copy()

    # Filtra pelo Departamento selecionado na barra lateral
    if dept_logado != "Todos" and "departamento" in df_mon.columns:
        df_mon = df_mon[
            df_mon["departamento"].astype(str).str.upper() == dept_logado.upper()
        ].copy()
        if (
            df_comp is not None
            and not df_comp.empty
            and "departamento" in df_comp.columns
        ):
            df_comp = df_comp[
                df_comp["departamento"].astype(str).str.upper() == dept_logado.upper()
            ].copy()

    if df_mon.empty:
        st.info(
            f"Nenhum registro de avaliação encontrado para o departamento: **{dept_logado}**."
        )
        return

    # =========================================================
    # 🕵️ ÁREA DE FILTROS COMPACTOS (SDR e DATA)
    # =========================================================
    with st.container(border=True):
        col_f1, col_f2 = st.columns([1, 1.2])

        # Filtro 1: Seleção de SDR (Segura e sem admin mestre)
        with col_f1:
            lista_sdrs = sorted(list(df_mon["sdr"].dropna().unique()))
            lista_sdrs = [
                nome for nome in lista_sdrs if "admin" not in str(nome).lower()
            ]
            sdr_selecionado = st.selectbox(
                "👤 Filtrar por Colaborador:",
                ["Todos da Equipe"] + lista_sdrs,
                label_visibility="collapsed",
            )

        # Filtro 2: Seleção de Data
        with col_f2:
            hoje = datetime.now().date()
            inicio_mes = hoje.replace(day=1)
            periodo = st.date_input(
                "📅 Período:",
                value=(inicio_mes, hoje),
                format="DD/MM/YYYY",
                label_visibility="collapsed",
            )

    # =========================================================
    # ⚙️ APLICAÇÃO DOS FILTROS
    # =========================================================
    df_mon["criado_em"] = pd.to_datetime(df_mon["criado_em"], errors="coerce")
    df_mon = df_mon.dropna(subset=["criado_em"]).copy()
    df_mon["data_filtro"] = df_mon["criado_em"].dt.date

    # 1. Filtra SDR
    if sdr_selecionado != "Todos da Equipe":
        df_mon = df_mon[df_mon["sdr"] == sdr_selecionado]
        if df_comp is not None and not df_comp.empty:
            df_comp = df_comp[df_comp["sdr_nome"] == sdr_selecionado]

    # 2. Filtra Data
    meses_selecionados = []
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
        df_mon = df_mon[
            (df_mon["data_filtro"] >= inicio) & (df_mon["data_filtro"] <= fim)
        ]
        # Mapeia os meses do período para filtrar o PDI (ex: '02/2026')
        meses_selecionados = (
            pd.date_range(inicio, fim, freq="MS").strftime("%m/%Y").tolist()
        )
        if inicio.strftime("%m/%Y") not in meses_selecionados:
            meses_selecionados.append(inicio.strftime("%m/%Y"))
    elif isinstance(periodo, tuple) and len(periodo) == 1:
        df_mon = df_mon[df_mon["data_filtro"] == periodo[0]]
        meses_selecionados = [periodo[0].strftime("%m/%Y")]

    if df_mon.empty:
        st.warning("Nenhum registro técnico encontrado neste período específico.")
        return

    # =========================================================
    # 📈 KPIs EXECUTIVOS (CARDS PREMIUM)
    # =========================================================
    df_mon["nota"] = pd.to_numeric(df_mon["nota"], errors="coerce").fillna(0)
    qtd_monitorias = len(df_mon)
    media_qa = df_mon["nota"].mean()

    # Cálculo PDI
    media_pdi_pct = 0.0
    if df_comp is not None and not df_comp.empty and meses_selecionados:
        df_comp_filtrado = df_comp[df_comp["mes_referencia"].isin(meses_selecionados)]
        if not df_comp_filtrado.empty:
            media_pdi_bruta = (
                df_comp_filtrado["media_comportamental"].astype(float).mean()
            )
            media_pdi_pct = (media_pdi_bruta / 5.0) * 100

    # 👇 CORREÇÃO: Cálculo de Contestação com cruzamento relacional de tabelas
    taxa_contestacao = 0.0
    if df_cont is not None and not df_cont.empty:
        # Pega a lista de IDs das monitorias atuais na tela
        ids_monitorias_tela = df_mon["id"].astype(str).tolist()
        # Filtra a tabela de contestações apenas para as que correspondem a essas monitorias
        df_cont_filtrado = df_cont[df_cont["monitoria_id"].astype(str).isin(ids_monitorias_tela)]
        qtd_contestadas = len(df_cont_filtrado)
        
        taxa_contestacao = (qtd_contestadas / qtd_monitorias) * 100 if qtd_monitorias > 0 else 0

    def render_kpi_card(title, value, icon="", border_color=COR_PRINCIPAL):
        return f"""
        <div style="background-color: rgba(255,255,255,0.02); padding: 20px; border-radius: 12px; border-left: 5px solid {border_color}; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <p style="margin:0; font-size: 13px; color: {COR_TEXTO}; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">{icon} {title}</p>
            <h2 style="margin:10px 0 0 0; color: #fff; font-size: 32px; font-weight: 700;">{value}</h2>
        </div>
        """

    st.write("##")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            render_kpi_card(
                "Média Qualidade",
                f"{media_qa:.1f}%",
                "🎯",
                COR_SUCESSO if media_qa >= 90 else COR_PRINCIPAL,
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            render_kpi_card(
                "Média PDI",
                f"{media_pdi_pct:.1f}%" if media_pdi_pct > 0 else "N/A",
                "🧠",
                "#1f77b4",
            ),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            render_kpi_card("Total Avaliações", qtd_monitorias, "📋", "#A0AEC0"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            render_kpi_card(
                "Taxa Contestação", f"{taxa_contestacao:.1f}%", "⚖️", "#FFCC00"
            ),
            unsafe_allow_html=True,
        )

    st.write("##")
    st.divider()

    # =========================================================
    # 📊 GRÁFICOS DE TENDÊNCIA
    # =========================================================
    st.markdown(
        "<h4 style='font-size: 16px; color: #eee;'>📉 Evolução Técnica ao Longo do Tempo</h4>",
        unsafe_allow_html=True,
    )

    # Agrupa notas por data
    df_tendencia = df_mon.groupby("data_filtro")["nota"].mean().reset_index()
    df_tendencia.rename(
        columns={"data_filtro": "Data", "nota": "Média Diária"}, inplace=True
    )

    fig = px.area(
        df_tendencia,
        x="Data",
        y="Média Diária",
        markers=True,
        labels={"Data": "", "Média Diária": "Nota Técnica (%)"},
    )
    fig.update_traces(
        line_color=COR_PRINCIPAL,
        line_shape="spline",
        fillcolor="rgba(255, 122, 0, 0.1)",
    )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=COR_FUNDO_GRAFICO,
        plot_bgcolor=COR_FUNDO_GRAFICO,
        font={"color": COR_TEXTO},
        yaxis=dict(
            range=[0, 105],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False,
        ),
        xaxis=dict(showgrid=False, zeroline=False),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================================================
    # 🔄 CRUZAMENTO DE DADOS (MONITORIA + CONTESTAÇÃO)
    # =========================================================
    st.markdown("### 📋 Base de Dados Consolidada")
    st.caption(
        "Visão bruta das avaliações e contestações atreladas. Use o botão abaixo para baixar em planilha."
    )

    if df_cont is not None and not df_cont.empty:
        df_cont_resumo = df_cont[
            ["monitoria_id", "motivo", "resposta_admin", "status"]
        ].rename(
            columns={
                "motivo": "Motivo Contestação",
                "resposta_admin": "Resposta Gestão",
                "status": "Status Contestação",
            }
        )
        df_mon["id"] = df_mon["id"].astype(str)
        df_cont_resumo["monitoria_id"] = df_cont_resumo["monitoria_id"].astype(str)
        df_final = pd.merge(
            df_mon, df_cont_resumo, left_on="id", right_on="monitoria_id", how="left"
        )
        # 👇 CORREÇÃO: Aplica "Sim" ou "Não" na coluna Contestado com base no Merge
        df_final["Contestado"] = df_final["Status Contestação"].apply(lambda x: "Não" if pd.isna(x) else "Sim")
    else:
        df_final = df_mon.copy()
        df_final["Motivo Contestação"] = "-"
        df_final["Resposta Gestão"] = "-"
        df_final["Status Contestação"] = "-"
        df_final["Contestado"] = "Não"

    # Função para extrair apenas NC e NCG com segurança de tipo
    def processar_erros(detalhes):
        if not detalhes or not isinstance(detalhes, dict):
            return ""
        try:
            erros = [
                f"{k} ({v.get('nota', v) if isinstance(v, dict) else v})"
                for k, v in detalhes.items()
                if (isinstance(v, dict) and v.get("nota") in ["NC", "NCG", "NC Grave"])
                or (isinstance(v, str) and v in ["NC", "NCG", "NC Grave"])
            ]
            return " | ".join(erros) if erros else ""
        except:
            return ""

    try:
        df_final["Detalhes (Erros)"] = df_final["detalhes"].apply(processar_erros)
        df_final["Data Monitoria"] = (
            df_final["criado_em"].dt.strftime("%d/%m/%Y %H:%M").fillna("-")
        )

        cols_fillna = ["Motivo Contestação", "Resposta Gestão", "Status Contestação"]
        for c in cols_fillna:
            if c in df_final.columns:
                df_final[c] = df_final[c].fillna("-")

        colunas_ordenadas = [
            "Data Monitoria",
            "sdr",
            "nota",
            "monitor_responsavel",
            "Contestado",
            "Status Contestação",
            "Detalhes (Erros)",
            "observacoes",
            "link_selene",
            "link_nectar",
        ]

        cols_existentes = [c for c in colunas_ordenadas if c in df_final.columns]
        df_export = df_final[cols_existentes].copy()

        mapa_renomeacao = {
            "sdr": "Colaborador",
            "nota": "Nota Final (%)",
            "observacoes": "Feedback Geral",
            "monitor_responsavel": "Avaliador",
            "link_selene": "Link Selene",
            "link_nectar": "Link CRM",
        }
        df_export.rename(columns=mapa_renomeacao, inplace=True)

        # =========================================================
        # 👁️ PRÉVIA E DOWNLOAD
        # =========================================================
        st.dataframe(
            df_export,
            column_config={
                "Link Selene": st.column_config.LinkColumn("Gravação"),
                "Link CRM": st.column_config.LinkColumn("Card CRM"),
                "Nota Final (%)": st.column_config.ProgressColumn(
                    "Nota (%)", format="%d%%", min_value=0, max_value=100
                ),
            },
            hide_index=True,
            use_container_width=True,
            height=300,
        )

        st.write("##")
        # Botão centralizado e gigante
        c_vazio, c_btn, c_vazio2 = st.columns([1, 2, 1])
        with c_btn:
            csv = df_export.to_csv(sep=";", index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 BAIXAR BASE COMPLETA EM EXCEL (.CSV)",
                data=csv,
                file_name=f"BI_Qualidade_{dept_logado}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary",
            )

    except Exception as e:
        st.error(f"Erro ao gerar a tabela de exportação: {e}")