import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_all_records_db, supabase
from datetime import datetime, timedelta


def render_dashboard():
    # --- CORREÇÃO PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados.")
        return
    # -------------------------------------------------------

    # 🎨 PALETA DE CORES MODERNA (Laranja Tech / Dark Theme)
    COR_PRINCIPAL = "#FF7A00"  # Laranja vibrante principal
    COR_SECUNDARIA = "#FFA500"  # Laranja mais claro/amarelado
    COR_SUCESSO = "#00E676"  # Verde neon moderno
    COR_FUNDO_GRAFICO = "rgba(0,0,0,0)"
    COR_LINHA_GRADE = "rgba(255,255,255,0.05)"
    COR_TEXTO = "#A0AEC0"

    nivel_usuario = str(st.session_state.get("nivel", "SDR")).upper()
    nome_completo_logado = st.session_state.get("user_nome", "Usuário")
    dept_selecionado = st.session_state.get("departamento_selecionado", "Todos")

    # 1. Busca de Dados
    df = get_all_records_db("monitorias")
    df_cont = get_all_records_db("contestacoes")

    if df is None or df.empty:
        st.info("Nenhuma monitoria encontrada no banco de dados.")
        return

    # 2. TRATAMENTO SEGURO DE DADOS BASE
    df["nota"] = pd.to_numeric(df["nota"], errors="coerce").fillna(0)
    df["criado_em"] = pd.to_datetime(df["criado_em"], errors="coerce")
    df = df.dropna(subset=["criado_em"])
    df = df.sort_values(by="criado_em")

    # 🛡️ TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
    if nivel_usuario != "ADMIN":
        df = df[
            (df["sdr"] != "admin@grupoacelerador.com.br")
            & (df["monitor_responsavel"] != "admin@grupoacelerador.com.br")
        ].copy()

    # --- APLICA O FILTRO DE DEPARTAMENTO GLOBAL ---
    if dept_selecionado != "Todos" and "departamento" in df.columns:
        df = df[
            df["departamento"].astype(str).str.strip().str.upper()
            == dept_selecionado.strip().upper()
        ].copy()

    st.title(f"Dashboard de Inteligência - {dept_selecionado}")

    if df.empty:
        st.warning(f"Nenhuma monitoria encontrada para a equipe: {dept_selecionado}.")
        return

    # --- 1. SEÇÃO DE FILTROS SECUNDÁRIOS ---
    with st.container(border=True):
        c1, c2 = st.columns([1, 1.5])

        if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            lista_sdrs = sorted(df["sdr"].dropna().unique().tolist())
            sdr_escolhido = c1.selectbox(
                "Filtrar por Colaborador Avaliado:", ["Ver Todos"] + lista_sdrs
            )
        else:
            st.markdown(f"Visualizando resultados de: **{nome_completo_logado}**")
            sdr_escolhido = nome_completo_logado

        hoje = datetime.now().date()
        data_min = df["criado_em"].min().date()
        inicio_padrao = max(data_min, hoje - timedelta(days=30))

        intervalo_datas = c2.date_input(
            "Selecione o Período:", value=(inicio_padrao, hoje), max_value=hoje
        )

    # ==========================================================
    # 📊 PREPARAÇÃO DOS DADOS
    # ==========================================================
    df_ranking_base = df.copy()
    if isinstance(intervalo_datas, tuple) and len(intervalo_datas) == 2:
        df_ranking_base = df_ranking_base[
            (df_ranking_base["criado_em"].dt.date >= intervalo_datas[0])
            & (df_ranking_base["criado_em"].dt.date <= intervalo_datas[1])
        ]

    df_filtrado = df_ranking_base.copy()
    if nivel_usuario not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
        df_filtrado = df_filtrado[
            df_filtrado["sdr"].astype(str).str.strip().str.upper()
            == nome_completo_logado.strip().upper()
        ]
    elif sdr_escolhido != "Ver Todos":
        df_filtrado = df_filtrado[df_filtrado["sdr"] == sdr_escolhido]

    if df_filtrado.empty:
        st.warning(f"Sem dados para este período ou colaborador.")
        return

    ids_filtrados = df_filtrado["id"].tolist()
    media_nota = df_filtrado["nota"].mean()

    # KPIS
    falhas_criticas = len(df_filtrado[df_filtrado["nota"] == 0])
    taxa_falhas_criticas = (
        (falhas_criticas / len(df_filtrado)) * 100 if len(df_filtrado) > 0 else 0
    )

    # Processamento Seguro de Contestações
    df_cont_filtrado = pd.DataFrame()
    total_cont = pendentes = aceitas = taxa_contestacao = taxa_reversao = 0

    if df_cont is not None and not df_cont.empty:
        df_cont_filtrado = df_cont[df_cont["monitoria_id"].isin(ids_filtrados)].copy()
        if not df_cont_filtrado.empty:
            total_cont = len(df_cont_filtrado)
            pendentes = len(df_cont_filtrado[df_cont_filtrado["status"] == "Pendente"])
            aceitas = len(df_cont_filtrado[df_cont_filtrado["status"] == "Aceita"])
            taxa_contestacao = (
                (total_cont / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0
            )

    # Organizando o Dashboard em Abas Limpas
    aba_sdr, aba_ofensores, aba_auditoria = st.tabs(
        ["📈 Performance e Distribuição", "🎯 Mapa de Ofensores", "📋 Produtividade QA"]
    )

    # ==========================================================
    # ABA 1: PERFORMANCE SDR
    # ==========================================================
    with aba_sdr:

        # ----------------------------------------------------------
        # 1. SEÇÃO SUPERIOR: MÉTRICAS TIPO CARDS
        # ----------------------------------------------------------
        if nivel_usuario not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            st.markdown("### Suas Entregas Pessoais")
        else:
            st.markdown("### Resumo de Entregas")

        def render_kpi_card(
            title, value, subtitle="", icon="", border_color=COR_PRINCIPAL
        ):
            html = f"""
            <div style="background-color: rgba(255,255,255,0.02); padding: 20px; border-radius: 12px; border-left: 5px solid {border_color}; border-top: 1px solid rgba(255,255,255,0.05); border-right: 1px solid rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05); box-shadow: 0 8px 16px rgba(0,0,0,0.2); height: 100%;">
                <p style="margin:0; font-size: 12px; color: {COR_TEXTO}; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">{icon} {title}</p>
                <h2 style="margin:10px 0 5px 0; color: #fff; font-size: 32px; font-weight: 700;">{value}</h2>
                <p style="margin:0; font-size: 12px; color: #666;">{subtitle}</p>
            </div>
            """
            return html

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                render_kpi_card(
                    "Total Avaliado",
                    f"{len(df_filtrado)}",
                    "Monitorias no período",
                    "📋",
                    "#1f77b4",
                ),
                unsafe_allow_html=True,
            )
        with m2:
            cor_nota = (
                COR_SUCESSO
                if media_nota >= 90
                else (COR_SECUNDARIA if media_nota >= 70 else COR_PRINCIPAL)
            )
            sub_nota = f"Meta: 90% | {'Atingida' if media_nota >= 90 else 'Abaixo'}"
            st.markdown(
                render_kpi_card(
                    "Qualidade Média", f"{media_nota:.1f}%", sub_nota, "🎯", cor_nota
                ),
                unsafe_allow_html=True,
            )
        with m3:
            cor_falha = COR_PRINCIPAL if taxa_falhas_criticas > 15 else COR_SUCESSO
            st.markdown(
                render_kpi_card(
                    "Falha Crítica (Nota 0)",
                    f"{taxa_falhas_criticas:.1f}%",
                    f"{falhas_criticas} avaliações zeradas",
                    "⚠️",
                    cor_falha,
                ),
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                render_kpi_card(
                    "Contestações",
                    f"{taxa_contestacao:.1f}%",
                    f"{total_cont} tickets abertos",
                    "⚖️",
                    COR_SECUNDARIA,
                ),
                unsafe_allow_html=True,
            )

        st.write("##")
        st.divider()

        # ----------------------------------------------------------
        # 2. SEÇÃO INTERMÉDIA: RANKING ESTRATÉGICO (PÓDIO ALINHADO)
        # ----------------------------------------------------------
        mostrar_ranking = (
            nivel_usuario not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]
        ) or (sdr_escolhido == "Ver Todos")

        if mostrar_ranking:
            st.markdown("### Top 3 Performance")

            ranking = (
                df_ranking_base.groupby("sdr")
                .agg(nota_media=("nota", "mean"), qtd_mon=("id", "count"))
                .reset_index()
            )

            MINIMO_MONITORIAS = 3
            ranking = ranking[ranking["qtd_mon"] >= MINIMO_MONITORIAS]

            ranking = ranking.sort_values(
                by=["nota_media", "qtd_mon"],
                ascending=[False, False],
            ).reset_index(drop=True)

            if ranking.empty:
                st.info(
                    f"Aguardando dados... O pódio exige um mínimo de {MINIMO_MONITORIAS} monitorias por colaborador no período."
                )
            else:
                col_rank = st.columns(3)
                # Adicionado Emojis e Texto Mais Forte para Ênfase
                medalhas = ["🥇 1º LUGAR", "🥈 2º LUGAR", "🥉 3º LUGAR"]
                cores_podio = [COR_SECUNDARIA, "#C0C0C0", "#CD7F32"]

                for idx, (_, row) in enumerate(ranking.head(3).iterrows()):
                    try:
                        res_user = supabase.table("usuarios").select("foto_url").eq("nome", row["sdr"]).single().execute()  # type: ignore
                        foto_sdr = (
                            res_user.data.get("foto_url")
                            if isinstance(res_user.data, dict)
                            else None
                        )
                    except:
                        foto_sdr = None

                    with col_rank[idx]:
                        foto_html = (
                            f'<img src="{foto_sdr}" style="width: 75px; height: 75px; border-radius: 50%; object-fit: cover; border: 3px solid {cores_podio[idx]}; margin: 0 auto; display: block;">'
                            if foto_sdr
                            else f'<div style="width: 75px; height: 75px; border-radius: 50%; border: 3px solid {cores_podio[idx]}; margin: 0 auto; display: flex; align-items: center; justify-content: center; font-size: 40px; background-color: rgba(255,255,255,0.05); color: {cores_podio[idx]}; line-height: 1;">👤</div>'
                        )

                        # HTML BLINDADO (Sem linhas vazias para não quebrar no Streamlit)
                        # O bloco do Nome (height: 65px) trava a altura para alinhar a nota embaixo perfeitamente!
                        st.markdown(
                            f"""<div style="background-color: rgba(255,255,255,0.02); padding: 25px 15px; border-radius: 12px; border-top: 4px solid {cores_podio[idx]}; text-align: center; box-shadow: 0 6px 15px rgba(0,0,0,0.2);"><div style="margin-bottom: 20px;"><span style="background-color: {cores_podio[idx]}20; color: {cores_podio[idx]}; padding: 6px 15px; border-radius: 20px; font-size: 14px; font-weight: 900; letter-spacing: 1px; border: 1px solid {cores_podio[idx]}50; box-shadow: 0 0 10px {cores_podio[idx]}40;">{medalhas[idx]}</span></div><div style="height: 85px; display: flex; justify-content: center; align-items: center;">{foto_html}</div><div style="height: 65px; display: flex; flex-direction: column; justify-content: flex-start; align-items: center; overflow: hidden;"><b style="font-size: 16px; color: #fff; line-height: 1.2;">{row['sdr']}</b><span style="color: #888; font-size: 12px; margin-top: 4px;">{row['qtd_mon']} avaliações</span></div><div style="margin-top: 10px;"><h2 style="color: #fff; margin: 0; font-size: 32px; font-weight: 800;">{row['nota_media']:.1f}%</h2></div></div>""",
                            unsafe_allow_html=True,
                        )

                if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
                    with st.expander("Ver Ranking Completo da Equipe", expanded=False):
                        ranking.index = ranking.index + 1
                        st.dataframe(
                            ranking,
                            column_config={
                                "sdr": "Nome do Colaborador",
                                "nota_media": st.column_config.NumberColumn(
                                    "Média de Qualidade", format="%.1f%%"
                                ),
                                "qtd_mon": "Total de Avaliações",
                            },
                            use_container_width=True,
                        )
            st.write("##")
            st.divider()

        # ----------------------------------------------------------
        # 3. SEÇÃO INFERIOR: GRÁFICOS (DISTRIBUIÇÃO DA QUALIDADE E FUNIL)
        # ----------------------------------------------------------
        col_dist, col_funnel = st.columns([1.5, 1])

        with col_dist:
            st.markdown(
                "<h4 style='text-align: left; font-size: 15px; color: #eee;'>Curva de Distribuição de Qualidade</h4>",
                unsafe_allow_html=True,
            )
            st.caption("Volume de avaliações separadas por faixas de notas.")

            fig_dist = px.histogram(
                df_filtrado,
                x="nota",
                nbins=10,
                color_discrete_sequence=[COR_PRINCIPAL],
                labels={"nota": "Nota da Avaliação", "count": "Quantidade"},
            )
            fig_dist.update_traces(
                marker_line_width=1, marker_line_color="rgba(0,0,0,0.5)", opacity=0.8
            )
            fig_dist.update_layout(
                height=300,
                margin=dict(l=10, r=20, t=10, b=10),
                paper_bgcolor=COR_FUNDO_GRAFICO,
                plot_bgcolor=COR_FUNDO_GRAFICO,
                font={"color": COR_TEXTO},
                yaxis=dict(showgrid=True, gridcolor=COR_LINHA_GRADE, title=""),
                xaxis=dict(showgrid=False, title="Faixa de Notas (%)"),
            )
            st.plotly_chart(fig_dist, use_container_width=True)

        with col_funnel:
            st.markdown(
                "<h4 style='text-align: left; font-size: 15px; color: #eee;'>Funil de Retenção</h4>",
                unsafe_allow_html=True,
            )
            st.caption(
                "De todas as avaliações, quantas tiveram penalidades e foram contestadas."
            )
            com_erros = len(df_filtrado[df_filtrado["nota"] < 100])

            fig_funil = go.Figure(
                go.Funnel(
                    y=["Avaliadas", "Com Erros", "Contestadas", "Revertidas"],
                    x=[len(df_filtrado), com_erros, total_cont, aceitas],
                    textinfo="value+percent initial",
                    marker={
                        "color": ["#333333", COR_PRINCIPAL, COR_SECUNDARIA, COR_SUCESSO]
                    },
                    textfont=dict(color="white", size=13),
                )
            )
            fig_funil.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor=COR_FUNDO_GRAFICO,
                plot_bgcolor=COR_FUNDO_GRAFICO,
                font={"color": COR_TEXTO},
            )
            st.plotly_chart(fig_funil, use_container_width=True)

        st.divider()

        # Gráfico de Rosca de contestações no final caso existam dados
        if total_cont > 0:
            st.markdown("### Status das Contestações")
            df_status = df_cont_filtrado["status"].value_counts().reset_index()
            df_status.columns = ["Status", "Quantidade"]
            cores_pie = {
                "Aceita": "#00cc96",
                "Recusada": "#ff4b4b",
                "Pendente": "#ffcc00",
            }

            fig_pie = px.pie(
                df_status,
                names="Status",
                values="Quantidade",
                hole=0.65,
                color="Status",
                color_discrete_map=cores_pie,
            )
            fig_pie.update_layout(
                height=320,
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor=COR_FUNDO_GRAFICO,
                plot_bgcolor=COR_FUNDO_GRAFICO,
                font={"color": COR_TEXTO},
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
                ),
            )
            fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+value",
                textfont_color="white",
                hoverinfo="label+value+percent",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # ==========================================================
    # ABA 2: OFENSORES E EVOLUÇÃO (DADOS DE INTELIGÊNCIA)
    # ==========================================================
    with aba_ofensores:

        # --- EVOLUÇÃO NO TEMPO (LINHA SUAVE LARANJA) ---
        st.markdown("### Evolução Histórica")

        df_evolucao = df_filtrado.copy()
        df_evolucao["DataCurta"] = df_evolucao["criado_em"].dt.date
        df_agrupado = (
            df_evolucao.groupby("DataCurta")
            .agg(nota_media=("nota", "mean"))
            .reset_index()
        )

        fig_evolucao = px.area(
            df_agrupado,
            x="DataCurta",
            y="nota_media",
            markers=True,
            labels={"DataCurta": "", "nota_media": "Média de Nota (%)"},
        )
        fig_evolucao.update_traces(
            line_color=COR_PRINCIPAL,
            line_shape="spline",
            fillcolor="rgba(255, 122, 0, 0.1)",
        )
        fig_evolucao.update_yaxes(
            range=[0, 105], showgrid=True, gridcolor=COR_LINHA_GRADE, zeroline=False
        )
        fig_evolucao.update_xaxes(showgrid=False, zeroline=False)
        fig_evolucao.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor=COR_FUNDO_GRAFICO,
            plot_bgcolor=COR_FUNDO_GRAFICO,
            font={"color": COR_TEXTO},
            hovermode="x unified",
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)

        st.divider()

        # --- PROCESSAMENTO DE ERROS (OFENSORES) ---
        if "detalhes" in df_filtrado.columns:
            erros_dict = {}
            reincidencias = []

            for _, row in df_filtrado.iterrows():
                detalhes = row["detalhes"]
                if isinstance(detalhes, dict):
                    for criterio, info in detalhes.items():
                        nota_crit = (
                            info.get("nota", "C") if isinstance(info, dict) else info
                        )
                        if nota_crit in ["NC", "NC Grave", "NGC"]:
                            erros_dict[criterio] = erros_dict.get(criterio, 0) + 1
                            reinc_texto = (
                                str(criterio)[:60] + "..."
                                if len(str(criterio)) > 60
                                else str(criterio)
                            )
                            reincidencias.append(
                                {"Colaborador": row["sdr"], "Critério": reinc_texto}
                            )

            if erros_dict:
                st.markdown(
                    "<h4 style='font-size: 16px; color: #eee;'>Volume de Ofensores</h4>",
                    unsafe_allow_html=True,
                )
                st.caption("Quais regras são mais quebradas em toda a equipe?")

                df_erros = (
                    pd.DataFrame(
                        list(erros_dict.items()), columns=["Critério", "Ocorrências"]
                    )
                    .sort_values(by="Ocorrências", ascending=True)
                    .tail(10)
                )

                fig_pareto = px.bar(
                    df_erros,
                    x="Ocorrências",
                    y="Critério",
                    orientation="h",
                    text="Ocorrências",
                    color_discrete_sequence=[COR_PRINCIPAL],
                )
                fig_pareto.update_traces(
                    textposition="outside", marker_line_width=0, textfont_color="#fff"
                )
                fig_pareto.update_xaxes(
                    showgrid=True,
                    gridcolor=COR_LINHA_GRADE,
                    zeroline=False,
                    visible=False,
                )
                fig_pareto.update_yaxes(showgrid=False, zeroline=False, title="")
                fig_pareto.update_layout(
                    height=max(300, len(df_erros) * 45),
                    margin=dict(l=10, r=30, t=10, b=10),
                    paper_bgcolor=COR_FUNDO_GRAFICO,
                    plot_bgcolor=COR_FUNDO_GRAFICO,
                    font={"color": COR_TEXTO},
                )
                st.plotly_chart(fig_pareto, use_container_width=True)

                st.divider()

                st.markdown(
                    "<h4 style='font-size: 16px; color: #eee;'>Matriz de Reincidência (Heatmap)</h4>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    "Identifique rapidamente quem está errando qual etapa de forma constante para direcionar PDI."
                )

                if len(reincidencias) > 0 and nivel_usuario in [
                    "ADMIN",
                    "GESTAO",
                    "AUDITOR",
                    "GERENCIA",
                ]:
                    df_reinc = pd.DataFrame(reincidencias)
                    df_matriz = (
                        df_reinc.groupby(["Critério", "Colaborador"])
                        .size()
                        .reset_index(name="Frequência")
                    )

                    fig_heat = go.Figure(
                        data=go.Heatmap(
                            z=df_matriz["Frequência"],
                            x=df_matriz["Colaborador"],
                            y=df_matriz["Critério"],
                            colorscale=["#222222", COR_PRINCIPAL],
                            hoverongaps=False,
                            xgap=3,
                            ygap=3,
                        )
                    )
                    fig_heat.update_layout(
                        height=500,
                        margin=dict(l=10, r=10, t=10, b=50),
                        paper_bgcolor=COR_FUNDO_GRAFICO,
                        plot_bgcolor=COR_FUNDO_GRAFICO,
                        font={"color": COR_TEXTO},
                        xaxis=dict(tickangle=-45),
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
                else:
                    st.info(
                        "Visão de reincidência disponível apenas para líderes observando a equipe completa."
                    )

            else:
                st.success(
                    "Avaliações impecáveis! Nenhum erro grave registrado neste período."
                )

    # ==========================================================
    # ABA 3: PRODUTIVIDADE DA AUDITORIA
    # ==========================================================
    with aba_auditoria:
        if nivel_usuario in ["ADMIN", "GESTAO", "GERENCIA", "AUDITOR"]:
            st.markdown("### Entregas da Equipe de Qualidade")

            produtividade_auditor = (
                df_filtrado.groupby("monitor_responsavel")
                .agg(qtd_avaliacoes=("id", "count"), nota_media_dada=("nota", "mean"))
                .reset_index()
                .sort_values(by="qtd_avaliacoes", ascending=True)
            )

            if not produtividade_auditor.empty:
                fig_aud = px.bar(
                    produtividade_auditor,
                    x="qtd_avaliacoes",
                    y="monitor_responsavel",
                    orientation="h",
                    text="qtd_avaliacoes",
                    color="qtd_avaliacoes",
                    color_continuous_scale=["#333", COR_PRINCIPAL],
                    labels={"monitor_responsavel": "", "qtd_avaliacoes": ""},
                )
                fig_aud.update_traces(textposition="outside", textfont_color="#fff")
                fig_aud.update_xaxes(
                    showgrid=True,
                    gridcolor=COR_LINHA_GRADE,
                    zeroline=False,
                    visible=False,
                )
                fig_aud.update_yaxes(showgrid=False, zeroline=False)
                fig_aud.update_layout(
                    height=300,
                    showlegend=False,
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=30, t=10, b=10),
                    paper_bgcolor=COR_FUNDO_GRAFICO,
                    plot_bgcolor=COR_FUNDO_GRAFICO,
                    font={"color": COR_TEXTO},
                )
                st.plotly_chart(fig_aud, use_container_width=True)

            else:
                st.info("Não há dados de auditores para o período selecionado.")
        else:
            st.warning(
                "Você não tem permissão para visualizar a produtividade da equipe de auditoria."
            )
