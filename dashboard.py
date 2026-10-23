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

    # 👇 AQUI: Função para somar as penalidades de cada avaliação
    def calc_perdidos(detalhes):
        p = 0
        if isinstance(detalhes, dict):
            for k, info in detalhes.items():
                if isinstance(info, dict):
                    n = str(info.get("nota", ""))
                    if "NC" in n or "NGC" in n:
                        p += int(info.get("penalidade_aplicada", 0))
        return p

    df["pontos_perdidos"] = df["detalhes"].apply(calc_perdidos)

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
        
        # Como o pote é mensal, o padrão de visualização vai ser o 1º dia do mês até hoje
        inicio_mes_atual = hoje.replace(day=1)
        inicio_padrao = max(data_min, inicio_mes_atual)

        intervalo_datas = c2.date_input(
            "Selecione o Período (Pote de 100 pts):", value=(inicio_padrao, hoje), max_value=hoje
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
    
    # 👇 AQUI: Cálculo da Pontuação pelo método Acumulativo (Pote 100)
    total_perdido_periodo = df_filtrado["pontos_perdidos"].sum()
    nota_periodo = 100 - total_perdido_periodo

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
                if nota_periodo >= 90
                else (COR_SECUNDARIA if nota_periodo >= 70 else COR_PRINCIPAL)
            )
            # Se a nota ficar negativa, muda de cor e alerta visualmente
            cor_nota = "#ff4b4b" if nota_periodo < 0 else cor_nota
            
            sub_nota = f"Acumulado (-{total_perdido_periodo} pts perdidos)"
            st.markdown(
                render_kpi_card(
                    "Pontuação (Pote)", f"{nota_periodo} pts", sub_nota, "🏆", cor_nota
                ),
                unsafe_allow_html=True,
            )
        with m3:
            cor_falha = COR_PRINCIPAL if taxa_falhas_criticas > 15 else COR_SUCESSO
            st.markdown(
                render_kpi_card(
                    "Falhas Fatais (Zero)",
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
            st.markdown("### Top 3 Performance (Pote Acumulado)")

            # 👇 AQUI: Agrupa o ranking pelo Pote de 100 pontos
            ranking = (
                df_ranking_base.groupby("sdr")
                .agg(pontos_perdidos_totais=("pontos_perdidos", "sum"), qtd_mon=("id", "count"))
                .reset_index()
            )
            ranking["nota_final_pote"] = 100 - ranking["pontos_perdidos_totais"]

            MINIMO_MONITORIAS = 3
            ranking = ranking[ranking["qtd_mon"] >= MINIMO_MONITORIAS]

            ranking = ranking.sort_values(
                by=["nota_final_pote", "qtd_mon"],
                ascending=[False, False],
            ).reset_index(drop=True)

            if ranking.empty:
                st.info(
                    f"Aguardando dados... O pódio exige um mínimo de {MINIMO_MONITORIAS} monitorias por colaborador no período."
                )
            else:
                col_rank = st.columns(3)
                medalhas = ["🥇 1º LUGAR", "🥈 2º LUGAR", "🥉 3º LUGAR"]
                cores_podio = [COR_SUCESSO, "#C0C0C0", "#CD7F32"] # Dourado trocado para Verde (Sucesso)

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
                        
                        cor_texto_nota = "#ff4b4b" if row['nota_final_pote'] < 0 else "#fff"

                        st.markdown(
                            f"""<div style="background-color: rgba(255,255,255,0.02); padding: 25px 15px; border-radius: 12px; border-top: 4px solid {cores_podio[idx]}; text-align: center; box-shadow: 0 6px 15px rgba(0,0,0,0.2);"><div style="margin-bottom: 20px;"><span style="background-color: {cores_podio[idx]}20; color: {cores_podio[idx]}; padding: 6px 15px; border-radius: 20px; font-size: 14px; font-weight: 900; letter-spacing: 1px; border: 1px solid {cores_podio[idx]}50; box-shadow: 0 0 10px {cores_podio[idx]}40;">{medalhas[idx]}</span></div><div style="height: 85px; display: flex; justify-content: center; align-items: center;">{foto_html}</div><div style="height: 65px; display: flex; flex-direction: column; justify-content: flex-start; align-items: center; overflow: hidden;"><b style="font-size: 16px; color: #fff; line-height: 1.2;">{row['sdr']}</b><span style="color: #888; font-size: 12px; margin-top: 4px;">{row['qtd_mon']} avaliações</span></div><div style="margin-top: 10px;"><h2 style="color: {cor_texto_nota}; margin: 0; font-size: 32px; font-weight: 800;">{row['nota_final_pote']} pts</h2></div></div>""",
                            unsafe_allow_html=True,
                        )

                if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
                    with st.expander("Ver Ranking Completo da Equipe", expanded=False):
                        ranking.index = ranking.index + 1
                        st.dataframe(
                            ranking,
                            column_config={
                                "sdr": "Nome do Colaborador",
                                "nota_final_pote": st.column_config.NumberColumn(
                                    "Pontuação Pote (Base 100)", format="%d pts"
                                ),
                                "pontos_perdidos_totais": "Total Descontado",
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
                "<h4 style='text-align: left; font-size: 15px; color: #eee;'>Curva de Distribuição de Notas (Individuais)</h4>",
                unsafe_allow_html=True,
            )
            st.caption("Qual a nota que a equipe costuma tirar por ligação/card individual.")

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

        # 👇 AQUI: EVOLUÇÃO NO TEMPO (ACUMULADA NEGATIVA BASE 100)
        st.markdown("### 📉 Evolução do Pote de Pontos")
        st.caption("Demonstração gráfica de como os 100 pontos iniciais caíram ao longo do período filtrado (acumulado diário).")

        df_evolucao = df_filtrado.copy()
        df_evolucao["DataCurta"] = df_evolucao["criado_em"].dt.date
        
        # Agrupa os pontos perdidos no dia
        df_agrupado = (
            df_evolucao.groupby("DataCurta")
            .agg(perdido_dia=("pontos_perdidos", "sum"))
            .reset_index()
        )
        
        # Faz a subtração cumulativa a partir dos 100 pontos
        df_agrupado["nota_acumulada"] = 100 - df_agrupado["perdido_dia"].cumsum()

        fig_evolucao = px.area(
            df_agrupado,
            x="DataCurta",
            y="nota_acumulada",
            markers=True,
            labels={"DataCurta": "", "nota_acumulada": "Pontuação Acumulada"},
        )
        fig_evolucao.update_traces(
            line_color=COR_PRINCIPAL,
            line_shape="spline",
            fillcolor="rgba(255, 122, 0, 0.1)",
        )
        # Permite ver a queda abaixo de 0 com linha de marcação vermelha
        fig_evolucao.update_yaxes(
            showgrid=True, gridcolor=COR_LINHA_GRADE, zeroline=True, zerolinecolor="#ff4b4b", title="Pontos Sobrantes"
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
                    for chave_codigo, info in detalhes.items():
                        # Garante que info é um dicionário antes de tentar buscar dados
                        if isinstance(info, dict):
                            nota_crit = info.get("nota", "C")
                            
                            if nota_crit in ["NC", "NC Grave", "NGC"]:
                                # Puxa o texto real da regra e não o código
                                texto_real_regra = info.get("criterio", "Regra sem nome")
                                
                                erros_dict[texto_real_regra] = erros_dict.get(texto_real_regra, 0) + 1
                                
                                reinc_texto = (
                                    str(texto_real_regra)[:60] + "..."
                                    if len(str(texto_real_regra)) > 60
                                    else str(texto_real_regra)
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
                .agg(qtd_avaliacoes=("id", "count"))
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