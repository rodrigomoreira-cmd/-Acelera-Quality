
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_all_records_db

def render_meus_resultados():
    # 1. Identificação do Nível de Acesso
    nivel = st.session_state.get('nivel', 'SDR').upper()
    usuario_logado = st.session_state.get('user_nome')
    
    # 2. Busca de Dados no Banco
    df = get_all_records_db("monitorias")

    if df is not None and not df.empty:
        # Tratamento inicial dos dados
        df['sdr_fmt'] = df['sdr'].astype(str).str.strip()
        df['nota'] = pd.to_numeric(df['nota'], errors='coerce')
        df['criado_em'] = pd.to_datetime(df['criado_em'])
        
        # --- LÓGICA DO ADMIN VS SDR ---
        if nivel == "ADMIN":
            st.title("🔎 Análise Individual de Performance")
            st.markdown("Selecione um colaborador para ver a evolução detalhada dele.")
            
            # Lista única de SDRs ordenada
            lista_sdrs = sorted(df['sdr_fmt'].unique().tolist())
            
            # Caixa de seleção para o Admin
            sdr_alvo = st.selectbox("👤 Selecione o SDR:", lista_sdrs)
        else:
            # SDR vê apenas os próprios dados
            st.title(f"📈 Meus Resultados")
            st.markdown("Acompanhe sua evolução detalhada de qualidade.")
            sdr_alvo = usuario_logado

        # --- FILTRAGEM DOS DADOS ---
        # Filtra o dataframe pelo SDR alvo (seja o escolhido pelo Admin ou o próprio SDR)
        meus_dados = df[df['sdr_fmt'].str.upper() == str(sdr_alvo).upper()].copy()
        meus_dados = meus_dados.sort_values(by='criado_em')

        if meus_dados.empty:
            st.warning(f"⚠️ Nenhuma monitoria encontrada para **{sdr_alvo}**.")
            return

        # --- A. VISÃO GERAL (KPIs) ---
        media_atual = meus_dados['nota'].mean()
        total_mons = len(meus_dados)
        melhor_nota = meus_dados['nota'].max()
        
        ultimas_3 = meus_dados.tail(3)['nota'].mean()
        delta = ultimas_3 - media_atual

        with st.container(border=True):
            st.caption(f"Resumo de Performance: **{sdr_alvo}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Média Geral", f"{media_atual:.1f}%", delta=f"{delta:.1f}% (Recente)")
            c2.metric("Total Avaliações", total_mons)
            c3.metric("Melhor Nota", f"{melhor_nota}%")

        st.divider()

        # --- B. GRÁFICO 1: EVOLUÇÃO ---
        st.subheader(f"🚀 Curva de Evolução: {sdr_alvo}")
        
        fig = px.area(
            meus_dados, 
            x='criado_em', 
            y='nota',
            markers=True,
            labels={'criado_em': 'Data', 'nota': 'Nota'},
            color_discrete_sequence=['#ff4b4b']
        )
        
        fig.update_layout(
            height=350,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font={'color': 'white'},
            yaxis=dict(range=[0, 105], gridcolor='#333'),
            xaxis=dict(gridcolor='#333')
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- C. GRÁFICO 2: VELOCÍMETRO ---
        c_left, c_chart, c_right = st.columns([1, 2, 1])
        
        with c_chart:
            ultima_nota = meus_dados.iloc[-1]['nota']
            data_ultima = meus_dados.iloc[-1]['criado_em'].strftime('%d/%m/%Y')
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = ultima_nota,
                title = {'text': f"Última Nota ({data_ultima})", 'font': {'size': 20, 'color': 'white'}},
                number = {'suffix': "%", 'font': {'color': 'white', 'size': 40}},
                gauge = {
                    'axis': {'range': [0, 100], 'tickcolor': "white"},
                    'bar': {'color': "#ff4b4b"},
                    'bgcolor': "rgba(0,0,0,0)",
                    'borderwidth': 2,
                    'bordercolor': "#333",
                    'steps': [
                        {'range': [0, 70], 'color': '#333'},
                        {'range': [70, 90], 'color': '#444'},
                        {'range': [90, 100], 'color': '#555'}
                    ],
                    'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': 90}
                }
            ))
            fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_gauge, use_container_width=True)

        st.divider()

        # --- D. LISTA DE FEEDBACKS ---
        st.subheader("📝 Detalhamento dos Feedbacks")
        
        df_feed = meus_dados.sort_values(by='criado_em', ascending=False)

        for index, row in df_feed.iterrows():
            with st.container(border=True):
                col_data, col_nota = st.columns([4, 1])
                data_fmt = row['criado_em'].strftime('%d/%m/%Y')
                
                col_data.markdown(f"📅 **Data:** {data_fmt}")
                cor_nota = "green" if row['nota'] >= 90 else "orange" if row['nota'] >= 70 else "red"
                col_nota.markdown(f"### :{cor_nota}[{row['nota']}%]")
                
                if row.get('observacoes'):
                    st.info(f"💡 **Feedback:** {row['observacoes']}")
                else:
                    st.caption("Sem observações registradas.")

    else:
        st.info("O banco de dados de monitorias está vazio no momento.")
