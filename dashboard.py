import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_all_records_db, supabase
from datetime import datetime, timedelta

def render_dashboard():
    # 1. Identificação do Usuário por Nome Completo e Nível
    nivel_usuario = str(st.session_state.get('nivel', 'SDR')).upper()
    # Usamos o Nome Completo como chave de busca principal
    nome_completo_logado = st.session_state.get('user_nome', 'Usuário')

    # 2. Busca os dados no Supabase
    df = get_all_records_db("monitorias")
    
    if df is None or df.empty:
        st.info("💡 Nenhuma monitoria encontrada no banco de dados.")
        return

    # 3. Tratamento de Dados
    df['nota'] = pd.to_numeric(df['nota'], errors='coerce')
    
    if 'criado_em' in df.columns:
        df['criado_em'] = pd.to_datetime(df['criado_em'])
        # Ordenação cronológica para o gráfico
        df = df.sort_values(by='criado_em')
        df['data_formatada'] = df['criado_em'].dt.strftime('%d/%m/%Y')

    st.title("📊 Dashboard de Performance")

    # --- SEÇÃO DE FILTROS ---
    c1, c2 = st.columns([1, 1.5])
    
    if nivel_usuario == "ADMIN":
        # Admin seleciona qualquer Nome Completo que exista na coluna 'sdr'
        lista_sdrs = sorted(df['sdr'].unique().tolist())
        sdr_escolhido = c1.selectbox("Filtrar por SDR (Nome Completo):", ["Ver Todos"] + lista_sdrs)
    else:
        # SDR travado no próprio Nome Completo
        st.info(f"Visualizando resultados de: **{nome_completo_logado}**")
        sdr_escolhido = nome_completo_logado

    # Filtro de Data
    hoje = datetime.now().date()
    data_min = df['criado_em'].min().date() if not df.empty else hoje
    # Define início padrão em 30 dias atrás ou na data da primeira monitoria
    inicio_padrao = max(data_min, hoje - timedelta(days=30))
    
    intervalo_datas = c2.date_input(
        "Selecione o Período:", 
        value=(inicio_padrao, hoje),
        max_value=hoje
    )

    # 4. Aplicação Rígida dos Filtros no DataFrame
    df_filtrado = df.copy()
    
    # Filtro de Identidade (SDR vê apenas o dele)
    if nivel_usuario == "SDR":
        df_filtrado = df_filtrado[df_filtrado['sdr'] == nome_completo_logado]
    elif sdr_escolhido != "Ver Todos":
        df_filtrado = df_filtrado[df_filtrado['sdr'] == sdr_escolhido]

    # Filtro de Período
    if isinstance(intervalo_datas, tuple) and len(intervalo_datas) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['criado_em'].dt.date >= intervalo_datas[0]) & 
            (df_filtrado['criado_em'].dt.date <= intervalo_datas[1])
        ]

    # Verificação de dados após filtros
    if df_filtrado.empty:
        st.warning(f"⚠️ Nenhuma monitoria encontrada para os critérios selecionados.")
        return

    # --- KPI'S PRINCIPAIS ---
    m1, m2, m3 = st.columns(3)
    media_nota = df_filtrado['nota'].mean()
    total_mon = len(df_filtrado)
    
    m1.metric("Média de Qualidade", f"{media_nota:.1f}%")
    m2.metric("Total de Monitorias", total_mon)
    
    # Cálculo simples de evolução (comparando com a média total do filtro)
    m3.metric("Status", "Estável" if media_nota >= 90 else "Atenção", 
              delta="Meta 90%", delta_color="normal" if media_nota >= 90 else "inverse")

    st.divider()

    # --- GRÁFICOS ---
    
    # Gráfico de Evolução (Linha)
    fig_evolucao = px.line(
        df_filtrado, 
        x='data_formatada', 
        y='nota', 
        markers=True, 
        text='nota',
        title="Evolução de Qualidade no Período",
        labels={'data_formatada': 'Data', 'nota': 'Nota (%)'}
    )
    fig_evolucao.update_traces(textposition='top center', texttemplate='%{text}%')
    fig_evolucao.update_yaxes(range=[0, 110]) # Garante escala de 0 a 100+
    st.plotly_chart(fig_evolucao, use_container_width=True)

    # Se Admin estiver vendo "Ver Todos", mostra um ranking por SDR
    if nivel_usuario == "ADMIN" and sdr_escolhido == "Ver Todos":
        st.subheader("🏆 Ranking de Qualidade (Média)")
        ranking = df_filtrado.groupby('sdr')['nota'].mean().reset_index().sort_values(by='nota', ascending=False)
        fig_ranking = px.bar(ranking, x='sdr', y='nota', color='nota', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_ranking, use_container_width=True)

    # --- TABELA DE DETALHAMENTO ---
    st.subheader("📋 Detalhamento das Avaliações")
    
    # Preparamos uma versão limpa da tabela para exibição
    df_exibicao = df_filtrado[['data_formatada', 'sdr', 'nota', 'monitor_responsavel', 'observacoes']].copy()
    df_exibicao.columns = ['Data', 'SDR', 'Nota (%)', 'Monitor', 'Feedback/Obs']
    
    st.dataframe(
        df_exibicao.sort_values(by='Data', ascending=False),
        use_container_width=True, 
        hide_index=True
    )