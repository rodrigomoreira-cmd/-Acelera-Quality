import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_all_records_db


def render_meus_resultados():
    # 🎨 PALETA DE CORES SISTÊMICA (Laranja Tech)
    COR_PRINCIPAL = "#FF7A00"
    COR_SECUNDARIA = "#FFA500"
    COR_SUCESSO = "#00E676"
    COR_FUNDO_GRAFICO = "rgba(0,0,0,0)"
    COR_LINHA_GRADE = "rgba(255,255,255,0.05)"
    COR_TEXTO = "#A0AEC0"

    # 1. Identificação do Nível de Acesso
    nivel = str(st.session_state.get("nivel", "SDR")).upper()
    usuario_logado = st.session_state.get("user_nome", "Usuário")

    # 2. Busca de Dados no Banco
    df = get_all_records_db("monitorias")

    if df is not None and not df.empty:
        # Tratamento inicial dos dados com BLINDAGEM de erro (Pylance/Pandas)
        df["sdr_fmt"] = df["sdr"].astype(str).str.strip()
        df["nota"] = pd.to_numeric(df["nota"], errors="coerce").fillna(0)

        # Força conversão segura de data e remove as nulas
        df["criado_em"] = pd.to_datetime(df["criado_em"], errors="coerce")
        df = df.dropna(subset=["criado_em"])

        # ==========================================================
        # 🛡️ TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
        # ==========================================================
        if nivel != "ADMIN":
            df = df[
                (
                    ~df["sdr"]
                    .astype(str)
                    .str.contains("admin@grupoacelerador.com.br", na=False, case=False)
                )
                & (
                    ~df["monitor_responsavel"]
                    .astype(str)
                    .str.contains("admin@grupoacelerador.com.br", na=False, case=False)
                )
            ].copy()

        # --- LÓGICA DO ADMIN VS SDR ---
        if nivel in ["ADMIN", "GESTAO", "GERENCIA", "AUDITOR"]:
            st.title("🔎 Análise Individual de Performance")
            st.markdown("Selecione um colaborador para ver a evolução detalhada dele.")

            # Lista única de SDRs ordenada e SEM o Admin
            lista_sdrs = sorted(
                [
                    nome
                    for nome in df["sdr_fmt"].unique().tolist()
                    if "admin" not in str(nome).lower()
                ]
            )

            # Caixa de seleção para a liderança
            sdr_alvo = (
                st.selectbox("👤 Selecione o SDR:", lista_sdrs) if lista_sdrs else None
            )

            if not sdr_alvo:
                st.warning("Nenhum SDR disponível para análise.")
                return
        else:
            # SDR vê apenas os próprios dados
            st.title("📈 Meus Resultados")
            st.markdown("Acompanhe sua evolução detalhada de qualidade.")
            sdr_alvo = usuario_logado

        # --- FILTRAGEM DOS DADOS ---
        # Filtra o dataframe pelo SDR alvo
        meus_dados = df[df["sdr_fmt"].str.upper() == str(sdr_alvo).upper()].copy()
        meus_dados = meus_dados.sort_values(by="criado_em")

        if meus_dados.empty:
            st.warning(f"⚠️ Nenhuma monitoria encontrada para **{sdr_alvo}**.")
            return

        # --- A. VISÃO GERAL (KPIs PREMIUM) ---
        media_atual = float(meus_dados["nota"].mean())
        total_mons = len(meus_dados)
        melhor_nota = float(meus_dados["nota"].max())

        ultimas_3 = float(meus_dados.tail(3)["nota"].mean())
        delta = ultimas_3 - media_atual

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

        st.write("##")
        c1, c2, c3 = st.columns(3)

        with c1:
            cor_media = (
                COR_SUCESSO
                if media_atual >= 90
                else (COR_SECUNDARIA if media_atual >= 70 else COR_PRINCIPAL)
            )
            sinal_delta = "+" if delta >= 0 else ""
            st.markdown(
                render_kpi_card(
                    "Média Geral",
                    f"{media_atual:.1f}%",
                    f"Tendência recente: {sinal_delta}{delta:.1f}%",
                    "🎯",
                    cor_media,
                ),
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                render_kpi_card(
                    "Total Avaliações",
                    f"{total_mons}",
                    "Histórico completo",
                    "📋",
                    "#1f77b4",
                ),
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                render_kpi_card(
                    "Melhor Nota",
                    f"{melhor_nota:.0f}%",
                    "Seu recorde pessoal",
                    "🏆",
                    COR_SECUNDARIA,
                ),
                unsafe_allow_html=True,
            )

        st.write("##")
        st.divider()

        # --- B. GRÁFICO 1: EVOLUÇÃO ---
        st.markdown(
            f"<h4 style='font-size: 16px; color: #eee;'>🚀 Curva de Evolução: {sdr_alvo}</h4>",
            unsafe_allow_html=True,
        )

        fig = px.area(
            meus_dados,
            x="criado_em",
            y="nota",
            markers=True,
            labels={"criado_em": "", "nota": "Sua Nota (%)"},
        )

        # Estilo Laranja Tech com linha curvada
        fig.update_traces(
            line_color=COR_PRINCIPAL,
            line_shape="spline",
            fillcolor="rgba(255, 122, 0, 0.1)",
        )
        fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor=COR_FUNDO_GRAFICO,
            paper_bgcolor=COR_FUNDO_GRAFICO,
            font={"color": COR_TEXTO},
            yaxis=dict(
                range=[0, 105], showgrid=True, gridcolor=COR_LINHA_GRADE, zeroline=False
            ),
            xaxis=dict(showgrid=False, zeroline=False),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # --- C. GRÁFICO 2: VELOCÍMETRO (TERMÔMETRO RECENTE) ---
        c_left, c_chart, c_right = st.columns([1, 2, 1])

        with c_chart:
            st.markdown(
                "<h4 style='text-align: center; font-size: 16px; color: #eee;'>Desempenho na Última Monitoria</h4>",
                unsafe_allow_html=True,
            )

            ultima_nota = float(meus_dados.iloc[-1]["nota"])

            # CORREÇÃO: Verifica se a data existe antes de formatar
            data_raw = meus_dados.iloc[-1]["criado_em"]
            data_ultima = (
                data_raw.strftime("%d/%m/%Y") if pd.notna(data_raw) else "Data N/D"
            )

            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=ultima_nota,
                    number={
                        "suffix": "%",
                        "font": {"color": "white", "size": 45, "weight": "bold"},
                    },
                    gauge={
                        "axis": {"range": [0, 100], "tickcolor": "white"},
                        "bar": {"color": "#ffffff", "thickness": 0.2},
                        "bgcolor": "rgba(0,0,0,0)",
                        "borderwidth": 0,
                        "steps": [
                            {"range": [0, 70], "color": COR_PRINCIPAL},
                            {"range": [70, 90], "color": COR_SECUNDARIA},
                            {"range": [90, 100], "color": COR_SUCESSO},
                        ],
                        "threshold": {
                            "line": {"color": "white", "width": 4},
                            "thickness": 0.75,
                            "value": 90,
                        },
                    },
                )
            )
            fig_gauge.update_layout(
                height=280,
                margin=dict(l=20, r=20, t=20, b=10),
                paper_bgcolor=COR_FUNDO_GRAFICO,
                font={"color": COR_TEXTO},
            )
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.markdown(
                f"<p style='text-align: center; color: #888; font-size: 14px; margin-top: -30px;'>Aplicada em: {data_ultima}</p>",
                unsafe_allow_html=True,
            )

        st.divider()

        # --- D. LISTA DE FEEDBACKS (ESTILO MENSAGENS) ---
        st.markdown("### 📝 Detalhamento dos Feedbacks")
        st.caption("Acompanhe o que os auditores e líderes disseram nas suas últimas avaliações.")
        st.write("##")

        df_feed = meus_dados.sort_values(by="criado_em", ascending=False)

        for index, row in df_feed.iterrows():
            data_row = row["criado_em"]
            data_fmt = (
                data_row.strftime("%d/%m/%Y às %H:%M") if pd.notna(data_row) else "N/D"
            )
            nota_f = float(row["nota"])

            cor_nota = (
                COR_SUCESSO
                if nota_f >= 90
                else (COR_SECUNDARIA if nota_f >= 70 else COR_PRINCIPAL)
            )
            avaliador = str(row.get("monitor_responsavel", "Sistema"))
            obs = str(row.get("observacoes", ""))
            
            # 👇 CORREÇÃO: Resgata e injeta o feedback do gestor (1:1)
            resp_gestor = str(row.get("resposta_gestor", ""))
            html_gestor = ""
            if resp_gestor and resp_gestor.lower() not in ['nan', 'none', '']:
                html_gestor = f"""
                <div style="margin-top: 15px; padding: 12px; background-color: rgba(0, 230, 118, 0.1); border-left: 4px solid #00E676; border-radius: 8px;">
                    <span style="font-size: 13px; font-weight: bold; color: #00E676; text-transform: uppercase; letter-spacing: 0.5px;">🎯 Plano de Ação do Gestor (1:1)</span><br>
                    <span style="font-size: 14px; color: #eee; line-height: 1.5; display: inline-block; margin-top: 5px;">{resp_gestor}</span>
                </div>
                """

            # Layout em caixa de comentário premium
            st.markdown(
                f"""
            <div style="background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 15px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px; margin-bottom: 10px;">
                    <div>
                        <span style="font-size: 12px; color: #888;">📅 {data_fmt} &nbsp; | &nbsp; 🕵️ {avaliador}</span>
                    </div>
                    <div style="background-color: {cor_nota}15; color: {cor_nota}; padding: 2px 10px; border-radius: 12px; font-weight: bold; border: 1px solid {cor_nota}50;">
                        Nota: {nota_f}%
                    </div>
                </div>
                <div style="font-size: 14px; color: #ddd; line-height: 1.5; font-style: {'italic' if not obs or obs == 'nan' else 'normal'};">
                    {"💬 <b>Auditor:</b> " + obs if obs and obs != 'nan' else "Sem observações registradas para esta avaliação."}
                </div>
                {html_gestor}
            </div>
            """,
                unsafe_allow_html=True,
            )

    else:
        st.info("O banco de dados de monitorias está vazio no momento.")