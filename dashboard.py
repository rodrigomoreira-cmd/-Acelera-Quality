import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_all_records_db  
from engine import THEME, ASSERTIVITY_CUTOFF 

def render_dashboard():
    nivel = st.session_state.get('nivel', 'sdr').upper()
    
    # CSS para forçar o contraste de cores nos títulos e métricas
    st.markdown(f"""
        <style>
        h1, h2, h3 {{ color: {THEME['text']} !important; }}
        [data-testid="stMetricValue"] {{ color: {THEME['accent']} !important; }}
        </style>
    """, unsafe_allow_html=True)

    st.title(f"📊 Dashboard Performance - {'Gestão' if nivel == 'ADMIN' else st.session_state.user}")

    # 1. CARREGAMENTO E FILTRO
    df = get_all_records_db("monitorias")
    if df.empty:
        st.warning("Nenhum dado encontrado.")
        return

    df['data'] = pd.to_datetime(df['data'])
    df['MesAno'] = df['data'].dt.to_period('M').astype(str)

    if nivel == 'SDR':
        df = df[df['sdr'] == st.session_state.user]
    
    # 2. MÉTRICAS LATERAIS (KPIs)
    avg_score = df['nota'].mean()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Média de Assertividade", f"{avg_score:.1f}%")
    with col2:
        st.metric("Total Monitorias", len(df))
    with col3:
        status_pendente = len(df[df['status_contestacao'] == 'Pendente'])
        st.metric("Contestações Pendentes", status_pendente)

    st.divider()

    # 3. GRÁFICOS COM PALETA PRETO/LARANJA
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 Evolução Mensal")
        trend = df.groupby('MesAno')['nota'].mean().reset_index()
        fig_trend = px.line(
            trend, x='MesAno', y='nota', markers=True,
            color_discrete_sequence=[THEME['accent']] # Linha Laranja
        )
        # Ajuste de Layout: Fundo Preto, Eixos Brancos
        fig_trend.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=THEME['text'],
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#333333', range=[0, 105])
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        st.subheader("🎯 Distribuição de Notas")
        fig_dist = px.histogram(
            df, x="nota", nbins=10,
            color_discrete_sequence=[THEME['text']] # Barras Brancas para contraste
        )
        fig_dist.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=THEME['text'],
            bargap=0.1
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    # 4. RANKING PARA ADMIN
    if nivel == 'ADMIN':
        st.divider()
        st.subheader("🏆 Ranking de SDRs")
        ranking = df.groupby('sdr')['nota'].mean().sort_values(ascending=False).reset_index()
        
        fig_rank = px.bar(
            ranking, x='sdr', y='nota',
            color='nota',
            # Gradiente: Cinza (baixo) para Laranja (alto)
            color_continuous_scale=[[0, '#333333'], [1, THEME['accent']]]
        )
        fig_rank.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=THEME['text'],
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_rank, use_container_width=True)