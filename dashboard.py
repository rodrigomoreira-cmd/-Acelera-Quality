import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_all_records_db  
from engine import THEME, ASSERTIVITY_CUTOFF 

def render_dashboard():
    nivel = st.session_state.get('nivel', 'sdr').upper()
    
    # Título dinâmico
    st.title(f"📊 Dashboard Performance - {'Gestão' if nivel == 'ADMIN' else st.session_state.user}")

    # 1. CARREGAMENTO E TRATAMENTO
    df = get_all_records_db("monitorias")
    if df.empty:
        st.warning("Nenhum dado encontrado no banco de dados.")
        return

    df['data'] = pd.to_datetime(df['data'])
    df['MesAno'] = df['data'].dt.to_period('M').astype(str)

    if nivel == 'SDR':
        df = df[df['sdr'] == st.session_state.user]
    
    # 2. KPIs (Métricas)
    avg_score = df['nota'].mean()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Laranja se acima da meta, Branco se abaixo
        color_metric = "#f77a00" if avg_score >= 85 else "#FFFFFF"
        st.markdown(f"<p style='color:white; margin-bottom:-10px;'>Média de Assertividade</p><h2 style='color:{color_metric};'>{avg_score:.1f}%</h2>", unsafe_allow_html=True)
    with col2:
        st.metric("Total Monitorias", len(df))
    with col3:
        status_pendente = len(df[df['status_contestacao'] == 'Pendente'])
        st.metric("Contestações Pendentes", status_pendente)

    st.divider()

    # 3. GRÁFICOS COM LÓGICA DE GRADIENTE CONDICIONAL
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 Evolução Mensal")
        trend = df.groupby('MesAno')['nota'].mean().reset_index()
        
        # Gráfico de linha usando a cor de destaque (Laranja)
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=trend['MesAno'], y=trend['nota'],
            mode='lines+markers',
            line=dict(color='#f77a00', width=4),
            marker=dict(color='#FFFFFF', size=8)
        ))
        fig_trend.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color="white", xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', range=[0, 105])
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        st.subheader("🏆 Performance por Período")
        # Barras que mudam de cor conforme a nota
        fig_bars = go.Figure()
        
        for i, row in trend.iterrows():
            # Acima de 85: Laranja (#f77a00) | Abaixo de 84: Amarelo/Vermelho (#fcbf1f)
            color_bar = "#f77a00" if row['nota'] >= 85 else "#fcbf1f"
            line_bar = "#c36000" if row['nota'] >= 85 else "#dd492b"
            
            fig_bars.add_trace(go.Bar(
                x=[row['MesAno']], y=[row['nota']],
                marker=dict(color=color_bar, line=dict(color=line_bar, width=2)),
                showlegend=False
            ))

        fig_bars.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color="white", yaxis=dict(gridcolor='rgba(255,255,255,0.1)', range=[0, 105])
        )
        st.plotly_chart(fig_bars, use_container_width=True)

    # 4. RANKING PARA ADMIN (COM GRADIENTE)
    if nivel == 'ADMIN':
        st.divider()
        st.subheader("🥇 Ranking Geral de SDRs")
        ranking = df.groupby('sdr')['nota'].mean().sort_values(ascending=False).reset_index()
        
        fig_rank = go.Figure()
        
        for _, row in ranking.iterrows():
            c_top = "#f77a00" if row['nota'] >= 85 else "#fcbf1f"
            c_bottom = "#c36000" if row['nota'] >= 85 else "#dd492b"
            
            fig_rank.add_trace(go.Bar(
                x=[row['sdr']], y=[row['nota']],
                marker=dict(color=c_top, line=dict(color=c_bottom, width=2)),
                text=f"{row['nota']:.1f}%", textposition='auto',
                showlegend=False
            ))

        fig_rank.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color="white", xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', range=[0, 110])
        )
        st.plotly_chart(fig_rank, use_container_width=True)