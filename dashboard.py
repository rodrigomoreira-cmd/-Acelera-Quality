import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_all_records_db, supabase
from datetime import datetime, timedelta

def render_dashboard():
    nivel_usuario = str(st.session_state.get('nivel', 'SDR')).upper()
    nome_completo_logado = st.session_state.get('user_nome', 'Usuário')
    dept_selecionado = st.session_state.get('departamento_selecionado', 'Todos')

    # 1. Busca de Dados
    df = get_all_records_db("monitorias")
    df_cont = get_all_records_db("contestacoes")
    
    if df is None or df.empty:
        st.info("💡 Nenhuma monitoria encontrada no banco de dados.")
        return

    # 2. Tratamento de Dados Base
    df['nota'] = pd.to_numeric(df['nota'], errors='coerce')
    df['criado_em'] = pd.to_datetime(df['criado_em'])
    df = df.sort_values(by='criado_em')

    # --- NOVO: APLICA O FILTRO DE DEPARTAMENTO GLOBAL ---
    if dept_selecionado != "Todos" and 'departamento' in df.columns:
        df = df[df['departamento'].astype(str).str.strip().str.upper() == dept_selecionado.strip().upper()].copy()

    st.title(f"📊 Dashboard de Performance - {dept_selecionado}")

    if df.empty:
        st.warning(f"⚠️ Nenhuma monitoria encontrada para a equipe: {dept_selecionado}.")
        return

    # --- 1. SEÇÃO DE FILTROS SECUNDÁRIOS ---
    with st.container(border=True):
        c1, c2 = st.columns([1, 1.5])
        
        if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            lista_sdrs = sorted(df['sdr'].unique().tolist())
            sdr_escolhido = c1.selectbox("Filtrar por Colaborador:", ["Ver Todos"] + lista_sdrs)
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

    # Aplicação dos Filtros de Nome e Data
    df_filtrado = df.copy()
    
    if nivel_usuario not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
        df_filtrado = df_filtrado[df_filtrado['sdr'].str.strip().str.upper() == nome_completo_logado.strip().upper()]
    elif sdr_escolhido != "Ver Todos":
        df_filtrado = df_filtrado[df_filtrado['sdr'] == sdr_escolhido]

    if isinstance(intervalo_datas, tuple) and len(intervalo_datas) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['criado_em'].dt.date >= intervalo_datas[0]) & 
            (df_filtrado['criado_em'].dt.date <= intervalo_datas[1])
        ]

    if df_filtrado.empty:
        st.warning(f"⚠️ Sem dados para este período ou colaborador.")
        return
        
    ids_filtrados = df_filtrado['id'].tolist()

    # --- 2. RANKING ESTRATÉGICO (Top 3) ---
    if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR"] and sdr_escolhido == "Ver Todos":
        st.markdown("### 🏆 Elite da Qualidade (Ranking por Volume)")
        
        ranking = df_filtrado.groupby('sdr').agg(
            nota_media=('nota', 'mean'),
            qtd_mon=('id', 'count')
        ).reset_index()

        ranking = ranking.sort_values(
            by=['qtd_mon', 'nota_media'], 
            ascending=[False, False]
        ).reset_index(drop=True)
        
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
                    <div style="background-color: {cores[i]}15; padding: 15px; border-radius: 15px; border: 2px solid {cores[i]}; text-align: center; min-height: 220px;">
                        {foto_html}<br>
                        <span style="font-size: 25px;">{medalhas[i]}</span><br>
                        <b style="font-size: 14px;">{row['sdr']}</b><br>
                        <h4 style="margin: 5px 0; color: #ccc; font-weight: normal;">{row['qtd_mon']} Monitorias</h4>
                        <h2 style="color: {cores[i]}; margin:0;">{row['nota_media']:.1f}%</h2>
                    </div>
                """, unsafe_allow_html=True)
        st.divider()

    # --- 3. MÉTRICAS TIPO CARD (Qualidade da Equipe) ---
    media_nota = df_filtrado['nota'].mean()
    m1, m2, m3 = st.columns(3)
    m1.metric("Média de Qualidade", f"{media_nota:.1f}%")
    m2.metric("Total de Monitorias", len(df_filtrado))
    m3.metric("Meta", "90%", delta=f"{media_nota - 90:.1f}%" if media_nota else None)

    # --- NOVO: VELOCÍMETRO (GAUGE) ABAIXO DOS CARDS ---
    st.write("##")
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = media_nota,
        title = {'text': "Temperatura de Qualidade"},
        number = {'suffix': "%"},
        gauge = {
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 70], 'color': "#ff4b4b"},
                {'range': [70, 90], 'color': "#ffa500"},
                {'range': [90, 100], 'color': "#00cc96"}
            ],
            'threshold': {'line': {'color': "white", 'width': 4}, 'value': 90}
        }
    ))
    fig_gauge.update_layout(height=350, margin=dict(l=30, r=30, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig_gauge, use_container_width=True)

    # --- 3.5 SAÚDE DA QUALIDADE E CALIBRAÇÃO ---
    st.write("##")
    st.markdown("### ⚖️ Saúde da Qualidade e Calibração")
    
    df_cont_filtrado = pd.DataFrame()
    total_cont = pendentes = aceitas = taxa_contestacao = taxa_reversao = 0
    
    if df_cont is not None and not df_cont.empty:
        df_cont_filtrado = df_cont[df_cont['monitoria_id'].isin(ids_filtrados)].copy()
        
        if not df_cont_filtrado.empty:
            total_cont = len(df_cont_filtrado)
            pendentes = len(df_cont_filtrado[df_cont_filtrado['status'] == 'Pendente'])
            aceitas = len(df_cont_filtrado[df_cont_filtrado['status'] == 'Aceita'])
            
            taxa_contestacao = (total_cont / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0
            taxa_reversao = (aceitas / total_cont * 100) if total_cont > 0 else 0

    if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Contestadas", total_cont)
        c2.metric("Pendentes de Resposta", pendentes, delta="-SLA" if pendentes > 0 else "Limpo", delta_color="inverse")
        c3.metric("Taxa de Contestação", f"{taxa_contestacao:.1f}%", help="Porcentagem de monitorias que os SDRs reclamaram.")
        c4.metric("Contestações Aceitas (Reversão)", f"{taxa_reversao:.1f}%", help="Quantas vezes o Auditor aceitou a contestação e mudou a nota.")

    # --- FUNIL E DONUT ---
    st.write("##")
    c_graf_funil, c_graf_donut = st.columns([1.5, 1])
    
    with c_graf_funil:
        com_erros = len(df_filtrado[df_filtrado['nota'] < 100])
        funil_etapas = ['Total Avaliado', 'Avaliações c/ Erros', 'Contestações Abertas', 'Contestações Aceitas']
        funil_valores = [len(df_filtrado), com_erros, total_cont, aceitas]
        
        fig_funil = go.Figure(go.Funnel(
            y=funil_etapas,
            x=funil_valores,
            textinfo="value+percent initial",
            marker={"color": ["#1f77b4", "#ff7f0e", "#d62728", "#2ca02c"]}
        ))
        fig_funil.update_layout(
            title="🌪️ Funil de Qualidade", 
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)', 
            font={'color': "white"}
        )
        st.plotly_chart(fig_funil, use_container_width=True)

    with c_graf_donut:
        if total_cont > 0:
            df_status = df_cont_filtrado['status'].value_counts().reset_index()
            df_status.columns = ['Status', 'Quantidade']
            cores = {'Aceita': '#00cc66', 'Recusada': '#ff4b4b', 'Pendente': '#ffcc00'}
            fig_pie = px.pie(
                df_status, names='Status', values='Quantidade', 
                hole=0.4, color='Status', color_discrete_map=cores,
                title="⚖️ Status das Contestações"
            )
            fig_pie.update_layout(margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
            st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # --- GRÁFICO DE OFENSORES ---
    if 'detalhes' in df_filtrado.columns:
        erros_dict = {}
        for _, row in df_filtrado.iterrows():
            detalhes = row['detalhes']
            if isinstance(detalhes, dict):
                for criterio, info in detalhes.items():
                    nota_crit = info.get('nota', 'C') if isinstance(info, dict) else info
                    if nota_crit in ["NC", "NC Grave", "NGC"]:
                        erros_dict[criterio] = erros_dict.get(criterio, 0) + 1
        
        if erros_dict:
            df_erros = pd.DataFrame(list(erros_dict.items()), columns=['Critério', 'Ocorrências']).sort_values(by='Ocorrências', ascending=True)
            fig_pareto = px.bar(
                df_erros, x='Ocorrências', y='Critério', orientation='h',
                text='Ocorrências', color_discrete_sequence=['#ff4b4b'],
                title="📉 Principais Ofensores (Erros NC e NCG)"
            )
            fig_pareto.update_layout(height=450, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
            st.plotly_chart(fig_pareto, use_container_width=True)

    st.divider()

    # --- GRÁFICO DE EVOLUÇÃO ---
    fig_evolucao = px.area(
        df_filtrado, x='criado_em', y='nota', 
        markers=True, title="📈 Evolução das Notas no Tempo",
        labels={'criado_em': 'Data', 'nota': 'Nota (%)'},
        color_discrete_sequence=['#1f77b4']
    )
    fig_evolucao.update_yaxes(range=[0, 105])
    fig_evolucao.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig_evolucao, use_container_width=True)

    # --- RANKING COMPLETO (TABELA) ---
    if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR"] and sdr_escolhido == "Ver Todos":
        st.write("##")
        st.subheader("📊 Ranking Completo (Prioridade: Volume)")
        st.dataframe(
            ranking,
            column_config={
                "sdr": "Colaborador",
                "qtd_mon": st.column_config.NumberColumn("Qtd. Monitorias", format="%d 📊"),
                "nota_media": st.column_config.NumberColumn("Média de Qualidade", format="%.2f%%")
            },
            hide_index=True,
            use_container_width=True
        )