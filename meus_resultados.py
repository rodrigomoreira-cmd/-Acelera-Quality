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
        # Tratamento inicial dos dados com BLINDAGEM de erro
        df['sdr_fmt'] = df['sdr'].astype(str).str.strip()
        df['nota'] = pd.to_numeric(df['nota'], errors='coerce').fillna(0)
        
        # CORREÇÃO: Força conversão segura de data e remove as nulas
        df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
        df = df.dropna(subset=['criado_em'])
        
        # ==========================================================
        # 🛡️ TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
        # ==========================================================
        if nivel != "ADMIN":
            df = df[
                (~df['sdr'].str.contains('admin@grupoacelerador.com.br', na=False, case=False)) & 
                (~df['monitor_responsavel'].str.contains('admin@grupoacelerador.com.br', na=False, case=False))
            ].copy()

        # --- LÓGICA DO ADMIN VS SDR ---
        if nivel == "ADMIN":
            st.title("🔎 Análise Individual de Performance")
            st.markdown("Selecione um colaborador para ver a evolução detalhada dele.")
            
            # Lista única de SDRs ordenada e SEM o Admin
            lista_sdrs = sorted([nome for nome in df['sdr_fmt'].unique().tolist() if 'admin' not in str(nome).lower()])
            
            # Caixa de seleção para o Admin
            sdr_alvo = st.selectbox("👤 Selecione o SDR:", lista_sdrs) if lista_sdrs else None
            
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
            
            # CORREÇÃO: Verifica se a data existe antes de formatar
            data_raw = meus_dados.iloc[-1]['criado_em']
            data_ultima = data_raw.strftime('%d/%m/%Y') if pd.notna(data_raw) else "Data N/D"
            
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
                
                # CORREÇÃO: Blindagem de data na lista de feedbacks
                data_row = row['criado_em']
                data_fmt = data_row.strftime('%d/%m/%Y') if pd.notna(data_row) else "N/D"
                
                col_data.markdown(f"📅 **Data:** {data_fmt}")
                cor_nota = "green" if row['nota'] >= 90 else "orange" if row['nota'] >= 70 else "red"
                col_nota.markdown(f"### :{cor_nota}[{row['nota']}%]")
                
                if row.get('observacoes'):
                    st.info(f"💡 **Feedback:** {row['observacoes']}")
                else:
                    st.caption("Sem observações registradas.")

    else:
        st.info("O banco de dados de monitorias está vazio no momento.")