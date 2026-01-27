import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_all_records_db  # Importa a função de busca no Supabase
from engine import THEME, ASSERTIVITY_CUTOFF # Importa as configurações visuais

def render_dashboard():
    st.title("📊 Dashboard de Performance SDR")

    # 1. CARREGAMENTO DOS DADOS
    # Busca os dados na tabela 'monitorias' do Supabase
    with st.spinner("Carregando indicadores do banco de dados..."):
        df = get_all_records_db("monitorias")

    if df.empty:
        st.warning("Ainda não existem dados de monitoria registrados no Supabase.")
        return

    # --- TRATAMENTO DE DADOS ---
    df['data'] = pd.to_datetime(df['data'])
    df['MesAno'] = df['data'].dt.to_period('M').astype(str)

    # 2. FILTRO DE PRIVACIDADE
    # Se for nível SDR, ele só enxerga os próprios dados
    if st.session_state.get('nivel') == 'sdr':
        df = df[df['sdr'] == st.session_state.user]
        st.info(f"Exibindo performance individual: {st.session_state.user}")

    # 3. CÁLCULO DE MÉTRICAS (KPIs)
    avg_score = df['nota'].mean()
    total_calls = len(df)
    critical_nc = len(df[df['nota'] == 0])

    # Exibição dos Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Média de Assertividade",
            value=f"{avg_score:.1f}%",
            delta=f"{avg_score - ASSERTIVITY_CUTOFF:.1f}%",
            delta_color="normal" if avg_score >= ASSERTIVITY_CUTOFF else "inverse"
        )
    
    with col2:
        st.metric("Total de Monitorias", total_calls)
        
    with col3:
        st.metric("Notas Zero (NC Grave)", critical_nc)

    st.divider()

    # 4. GRÁFICOS VISUAIS
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Evolução Mensal")
        # Agrupamento para gráfico de linha
        trend = df.groupby('MesAno')['nota'].mean().reset_index()
        fig_trend = px.line(
            trend, 
            x='MesAno', 
            y='nota', 
            markers=True,
            color_discrete_sequence=[THEME['accent']]
        )
        fig_trend.update_layout(yaxis_range=[0, 105], template="plotly_dark")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        st.subheader("Distribuição de Notas")
        fig_dist = px.histogram(
            df, 
            x="nota", 
            nbins=10,
            color_discrete_sequence=[THEME['warning']]
        )
        fig_dist.update_layout(template="plotly_dark")
        st.plotly_chart(fig_dist, use_container_width=True)

    # 5. RANKING (Visível apenas para ADMIN)
    if st.session_state.get('nivel') == 'admin':
        st.divider()
        st.subheader("🏆 Ranking de Assertividade por SDR")
        ranking = df.groupby('sdr')['nota'].mean().sort_values(ascending=False).reset_index()
        
        fig_rank = px.bar(
            ranking, 
            x='sdr', 
            y='nota', 
            color='nota',
            color_continuous_scale=[THEME['error'], THEME['warning'], THEME['success']]
        )
        fig_rank.update_layout(template="plotly_dark")
        st.plotly_chart(fig_rank, use_container_width=True)