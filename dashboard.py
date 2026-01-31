import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_all_records_db, supabase
from datetime import datetime, timedelta

# REMOVIDA: A função render_notificacoes foi removida daqui para centralizar no app.py/contestacao.py
# REMOVIDA: A função marcar_como_lida foi removida daqui para evitar duplicidade de lógica

def render_dashboard():
    nivel_usuario = str(st.session_state.get('nivel', 'SDR')).upper()
    nome_completo_logado = st.session_state.get('user_nome', 'Usuário')

    # 1. Busca de Dados
    df = get_all_records_db("monitorias")
    
    if df is None or df.empty:
        st.info("💡 Nenhuma monitoria encontrada no banco de dados.")
        return

    # 2. Tratamento de Dados
    df['nota'] = pd.to_numeric(df['nota'], errors='coerce')
    df['criado_em'] = pd.to_datetime(df['criado_em'])
    df = df.sort_values(by='criado_em')

    # Título principal agora sem avisos em cima
    st.title("📊 Dashboard de Performance")

    # --- 1. SEÇÃO DE FILTROS ---
    with st.container(border=True):
        c1, c2 = st.columns([1, 1.5])
        
        if nivel_usuario == "ADMIN":
            lista_sdrs = sorted(df['sdr'].unique().tolist())
            sdr_escolhido = c1.selectbox("Filtrar por SDR:", ["Ver Todos"] + lista_sdrs)
        else:
            st.markdown(f"Visualizando resultados de: **{nome_completo_logado}**")
            sdr_escolhido = nome_completo_logado

        hoje = datetime.now().date()
        data_min = df['criado_em'].min().date()
        inicio_padrao = max(data_min, hoje - timedelta(days=30))
        
        intervalo_datas = c2.date_input(
            "Selecione o Período:", 
            value=(inicio_padrao, hoje),
            max_value=hoje
        )

    # Aplicação dos Filtros
    df_filtrado = df.copy()
    if nivel_usuario == "SDR":
        df_filtrado = df_filtrado[df_filtrado['sdr'] == nome_completo_logado]
    elif sdr_escolhido != "Ver Todos":
        df_filtrado = df_filtrado[df_filtrado['sdr'] == sdr_escolhido]

    if isinstance(intervalo_datas, tuple) and len(intervalo_datas) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['criado_em'].dt.date >= intervalo_datas[0]) & 
            (df_filtrado['criado_em'].dt.date <= intervalo_datas[1])
        ]

    if df_filtrado.empty:
        st.warning(f"⚠️ Sem dados para este período.")
        return

    # --- 2. RANKING TOP 3 (Apenas Admin vendo "Ver Todos") ---
    if nivel_usuario == "ADMIN" and sdr_escolhido == "Ver Todos":
        st.markdown("### 🏆 Elite da Qualidade (Top 3)")
        ranking = df_filtrado.groupby('sdr')['nota'].mean().sort_values(ascending=False).reset_index()
        
        col_rank = st.columns(3)
        medalhas = ["🥇", "🥈", "🥉"]
        cores = ["#FFD700", "#C0C0C0", "#CD7F32"]

        for i, row in ranking.head(3).iterrows():
            try:
                res_user = supabase.table("usuarios").select("foto_url").eq("nome", row['sdr']).single().execute()
                foto_sdr = res_user.data.get('foto_url') if res_user.data else None
            except:
                foto_sdr = None
            
            with col_rank[i]:
                foto_html = f'<img src="{foto_sdr}" style="width: 70px; height: 70px; border-radius: 50%; object-fit: cover; border: 3px solid {cores[i]};">' if foto_sdr else '<div style="font-size: 40px;">👤</div>'
                st.markdown(f"""
                    <div style="background-color: {cores[i]}15; padding: 15px; border-radius: 15px; border: 2px solid {cores[i]}; text-align: center;">
                        {foto_html}<br>
                        <span style="font-size: 25px;">{medalhas[i]}</span><br>
                        <b>{row['sdr']}</b><br>
                        <h3 style="color: {cores[i]}; margin:0;">{row['nota']:.1f}%</h3>
                    </div>
                """, unsafe_allow_html=True)
        st.divider()

    # --- 3. MÉTRICAS TIPO CARD ---
    media_nota = df_filtrado['nota'].mean()
    m1, m2, m3 = st.columns(3)
    m1.metric("Média de Qualidade", f"{media_nota:.1f}%")
    m2.metric("Total de Monitorias", len(df_filtrado))
    m3.metric("Meta", "90%", delta=f"{media_nota - 90:.1f}%" if media_nota else None)

    # --- 4. VELOCÍMETRO ---
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = media_nota,
        title = {'text': "Média Geral", 'font': {'size': 18}},
        number = {'suffix': "%"},
        gauge = {
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 70], 'color': "#ff4b4b"},
                {'range': [70, 90], 'color': "#ffa500"},
                {'range': [90, 100], 'color': "#00cc96"}
            ],
            'threshold': {'line': {'color': "black", 'width': 4}, 'value': 90}
        }
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=30, r=30, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig_gauge, use_container_width=True)

    # --- 5. GRÁFICO DE EVOLUÇÃO ---
    fig_evolucao = px.area(
        df_filtrado, x='criado_em', y='nota', 
        markers=True, title="Evolução das Notas",
        labels={'criado_em': 'Data', 'nota': 'Nota (%)'},
        color_discrete_sequence=['#1f77b4']
    )
    fig_evolucao.update_yaxes(range=[0, 105])
    fig_evolucao.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig_evolucao, use_container_width=True)

    # --- 6. TABELA DETALHADA ---
    with st.expander("📋 Ver Histórico Detalhado"):
        df_exibicao = df_filtrado[['criado_em', 'sdr', 'nota', 'monitor_responsavel', 'observacoes']].copy()
        df_exibicao['criado_em'] = df_exibicao['criado_em'].dt.strftime('%d/%m/%Y %H:%M')
        st.dataframe(df_exibicao.sort_values(by='criado_em', ascending=False), use_container_width=True, hide_index=True)