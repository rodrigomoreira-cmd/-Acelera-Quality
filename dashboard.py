import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_all_records_db  
from engine import THEME, ASSERTIVITY_CUTOFF 

def render_dashboard():
    # Ajusta o título com base no nível para personalização
    nivel = st.session_state.get('nivel', 'sdr').upper()
    
    if nivel == 'ADMIN':
        st.title("📊 Dashboard de Performance - Visão Gestor")
    else:
        st.title(f"📊 Minha Performance - {st.session_state.user}")

    # 1. CARREGAMENTO DOS DADOS
    with st.spinner("Carregando indicadores do banco de dados..."):
        df = get_all_records_db("monitorias")

    if df.empty:
        st.warning("Ainda não existem dados de monitoria registrados no Supabase.")
        return

    # --- TRATAMENTO DE DADOS ---
    df['data'] = pd.to_datetime(df['data'])
    df['MesAno'] = df['data'].dt.to_period('M').astype(str)

    # 2. FILTRO DE PRIVACIDADE (Refinado)
    if nivel == 'SDR':
        # SDR só enxerga os próprios dados
        df = df[df['sdr'] == st.session_state.user]
        if df.empty:
            st.info("Você ainda não possui monitorias registradas para gerar indicadores.")
            return
    else:
        st.info("💡 Visão de Administrador: Dados consolidados de toda a equipe.")

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
        # Mostra o total de Notas Zero (NC Grave)
        st.metric("Notas Zero (NC Grave)", critical_nc, delta="Atenção" if critical_nc > 0 else None, delta_color="inverse")

    st.divider()

    # 4. GRÁFICOS VISUAIS
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 Evolução de Nota")
        # Agrupamento para gráfico de linha
        trend = df.groupby('MesAno')['nota'].mean().reset_index()
        fig_trend = px.line(
            trend, 
            x='MesAno', 
            y='nota', 
            markers=True,
            labels={'nota': 'Média Nota', 'MesAno': 'Período'},
            color_discrete_sequence=[THEME['accent']]
        )
        fig_trend.update_layout(yaxis_range=[0, 105], template="plotly_dark")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_right:
        st.subheader("🎯 Distribuição de Resultados")
        fig_dist = px.histogram(
            df, 
            x="nota", 
            nbins=10,
            labels={'nota': 'Faixa de Nota', 'count': 'Frequência'},
            color_discrete_sequence=[THEME['warning']]
        )
        fig_dist.update_layout(template="plotly_dark", bargap=0.1)
        st.plotly_chart(fig_dist, use_container_width=True)

    # 5. RANKING E GESTÃO (Visível apenas para ADMIN)
    if nivel == 'ADMIN':
        st.divider()
        st.subheader("🏆 Ranking de Assertividade por SDR")
        
        # Ranking consolidado
        ranking = df.groupby('sdr')['nota'].mean().sort_values(ascending=False).reset_index()
        
        fig_rank = px.bar(
            ranking, 
            x='sdr', 
            y='nota', 
            text_auto='.1f',
            color='nota',
            labels={'sdr': 'SDR', 'nota': 'Média de Nota'},
            color_continuous_scale=[THEME['error'], THEME['warning'], THEME['success']]
        )
        fig_rank.update_layout(template="plotly_dark", coloraxis_showscale=False)
        st.plotly_chart(fig_rank, use_container_width=True)
        
        # Indicador de Contestações Pendentes (Extra para o Admin)
        if 'status_contestacao' in df.columns:
            pendentes = len(df[df['status_contestacao'] == 'Pendente'])
            if pendentes > 0:
                st.warning(f"🔔 Existem {pendentes} contestações aguardando sua resposta na aba de Contestações.")