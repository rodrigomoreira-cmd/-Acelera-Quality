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

    # 2. TRATAMENTO SEGURO DE DADOS BASE (Proteção contra erros .dt)
    df['nota'] = pd.to_numeric(df['nota'], errors='coerce').fillna(0)
    
    # Converte para datetime e remove registros corrompidos antes de ordenar
    df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce')
    df = df.dropna(subset=['criado_em'])
    df = df.sort_values(by='criado_em')

    # ==========================================================
    # 🛡️ TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
    # ==========================================================
    if nivel_usuario != "ADMIN":
        df = df[
            (df['sdr'] != 'admin@grupoacelerador.com.br') & 
            (df['monitor_responsavel'] != 'admin@grupoacelerador.com.br')
        ].copy()

    # --- APLICA O FILTRO DE DEPARTAMENTO GLOBAL ---
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
            lista_sdrs = sorted(df['sdr'].dropna().unique().tolist())
            sdr_escolhido = c1.selectbox("Filtrar por Colaborador Avaliado:", ["Ver Todos"] + lista_sdrs)
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
    
    # Tratamento de string mais seguro
    if nivel_usuario not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
        df_filtrado = df_filtrado[df_filtrado['sdr'].astype(str).str.strip().str.upper() == nome_completo_logado.strip().upper()]
    elif sdr_escolhido != "Ver Todos":
        df_filtrado = df_filtrado[df_filtrado['sdr'] == sdr_escolhido]

    if isinstance(intervalo_datas, tuple) and len(intervalo_datas) == 2:
        # Pega as datas com segurança
        df_filtrado = df_filtrado[
            (df_filtrado['criado_em'].dt.date >= intervalo_datas[0]) & 
            (df_filtrado['criado_em'].dt.date <= intervalo_datas[1])
        ]

    if df_filtrado.empty:
        st.warning(f"⚠️ Sem dados para este período ou colaborador.")
        return
        
    ids_filtrados = df_filtrado['id'].tolist()
    media_nota = df_filtrado['nota'].mean()

    # Processamento Seguro de Contestações
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

    # Organizando o Dashboard em Abas
    aba_sdr, aba_ofensores, aba_auditoria = st.tabs([
        "🎯 Performance (SDR)", 
        "📉 Ofensores e Evolução", 
        "🕵️ Produtividade (Qualidade)"
    ])

    # ==========================================================
    # ABA 1: PERFORMANCE SDR
    # ==========================================================
    with aba_sdr:
        
        # ----------------------------------------------------------
        # 1. RANKING ESTRATÉGICO (Top 3)
        # ----------------------------------------------------------
        if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"] and sdr_escolhido == "Ver Todos":
            st.markdown("### 🏆 Elite da Qualidade (Top 3)")
            
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

        # ----------------------------------------------------------
        # 2. MÉTRICAS TIPO CARDS
        # ----------------------------------------------------------
        st.markdown("### 🎯 Resumo de Entregas")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Monitorias", len(df_filtrado))
        m2.metric("Média de Qualidade", f"{media_nota:.1f}%", delta=f"{media_nota - 90:.1f}%" if pd.notna(media_nota) else None, help="A meta de qualidade é 90%")
        m3.metric("Meta do Período", "90%")
        
        if nivel_usuario in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            st.write("##")
            c1, c2, c3 = st.columns(3)
            c1.metric("Volume Contestadas", total_cont)
            c2.metric("Taxa de Contestação", f"{taxa_contestacao:.1f}%")
            c3.metric("Taxa de Reversão", f"{taxa_reversao:.1f}%", help="Porcentagem de contestações que foram aceitas")
        
        st.divider()

        # ----------------------------------------------------------
        # 3. VELOCÍMETRO (TEMPERATURA)
        # ----------------------------------------------------------
        st.markdown("### 🌡️ Temperatura Geral")
        col_vazia1, col_gauge, col_vazia2 = st.columns([1, 2, 1])
        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = media_nota if pd.notna(media_nota) else 0,
                number = {'suffix': "%", 'font': {'color': "white"}},
                gauge = {
                    'axis': {'range': [0, 100], 'tickcolor': "white"},
                    'steps': [
                        {'range': [0, 70], 'color': "#ff4b4b"},
                        {'range': [70, 90], 'color': "#ffa500"},
                        {'range': [90, 100], 'color': "#00cc96"}
                    ],
                    'threshold': {'line': {'color': "white", 'width': 4}, 'value': 90}
                }
            ))
            fig_gauge.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
            st.plotly_chart(fig_gauge, use_container_width=True)

        st.divider()

        # ----------------------------------------------------------
        # 4. FUNIL DE CONVERSÃO
        # ----------------------------------------------------------
        st.markdown("### 🌪️ Funil de Conversão da Qualidade")
        com_erros = len(df_filtrado[df_filtrado['nota'] < 100])
        funil_etapas = ['Total Avaliado', 'Avaliações c/ Erros', 'Contestações Abertas', 'Contestações Aceitas']
        funil_valores = [len(df_filtrado), com_erros, total_cont, aceitas]
        
        fig_funil = go.Figure(go.Funnel(
            y=funil_etapas, x=funil_valores,
            textinfo="value+percent initial",
            marker={"color": ["#1f77b4", "#ff7f0e", "#d62728", "#2ca02c"]},
            textfont=dict(color="white")
        ))
        fig_funil.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_funil, use_container_width=True)

        st.divider()

        # ----------------------------------------------------------
        # 5. GRÁFICO DE ROSCA
        # ----------------------------------------------------------
        st.markdown("### ⚖️ Status das Contestações")
        if total_cont > 0:
            df_status = df_cont_filtrado['status'].value_counts().reset_index()
            df_status.columns = ['Status', 'Quantidade']
            cores = {'Aceita': '#00cc66', 'Recusada': '#ff4b4b', 'Pendente': '#ffcc00'}
            
            fig_pie = px.pie(
                df_status, names='Status', values='Quantidade', 
                hole=0.5, color='Status', color_discrete_map=cores
            )
            fig_pie.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, showlegend=True)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label+value', textfont_color="white")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Nenhuma contestação aberta neste período.")

    # ==========================================================
    # ABA 2: OFENSORES E EVOLUÇÃO
    # ==========================================================
    with aba_ofensores:
        st.markdown("### 📉 Principais Ofensores (Erros Graves)")
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
                    text='Ocorrências', color_discrete_sequence=['#ff4b4b']
                )
                fig_pareto.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                st.plotly_chart(fig_pareto, use_container_width=True)
            else:
                st.success("Nenhum erro grave (NC/NCG) registrado neste período!")

        st.divider()
        st.markdown("### 📈 Evolução das Notas no Tempo")
        fig_evolucao = px.area(
            df_filtrado, x='criado_em', y='nota', 
            markers=True, labels={'criado_em': 'Data', 'nota': 'Nota (%)'},
            color_discrete_sequence=['#1f77b4']
        )
        fig_evolucao.update_yaxes(range=[0, 105])
        fig_evolucao.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_evolucao, use_container_width=True)

    # ==========================================================
    # ABA 3: PRODUTIVIDADE DA AUDITORIA
    # ==========================================================
    with aba_auditoria:
        if nivel_usuario in ["ADMIN", "GESTAO", "GERENCIA", "AUDITOR"]:
            st.markdown("### 🕵️ Entregas da Equipe de Qualidade")
            st.markdown("Acompanhe o volume de avaliações realizadas por cada Auditor/Gestor.")
            
            produtividade_auditor = df_filtrado.groupby('monitor_responsavel').agg(
                qtd_avaliacoes=('id', 'count'),
                nota_media_dada=('nota', 'mean')
            ).reset_index().sort_values(by='qtd_avaliacoes', ascending=False)
            
            if not produtividade_auditor.empty:
                fig_aud = px.bar(
                    produtividade_auditor.sort_values('qtd_avaliacoes', ascending=True), 
                    x='qtd_avaliacoes', y='monitor_responsavel', orientation='h',
                    text='qtd_avaliacoes', color='qtd_avaliacoes',
                    color_continuous_scale='Blues',
                    labels={'monitor_responsavel': 'Avaliador', 'qtd_avaliacoes': 'Nº de Avaliações'}
                )
                fig_aud.update_layout(height=400, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                st.plotly_chart(fig_aud, use_container_width=True)
                
                st.divider()
                st.markdown("#### Detalhamento por Avaliador")
                
                st.dataframe(
                    produtividade_auditor,
                    column_config={
                        "monitor_responsavel": "Avaliador",
                        "qtd_avaliacoes": st.column_config.NumberColumn("Monitorias Entregues", format="%d 📊"),
                        "nota_media_dada": st.column_config.NumberColumn("Média Distribuída", format="%.1f%%")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Não há dados de auditores para o período selecionado.")
        else:
            st.warning("⚠️ Você não tem permissão para visualizar a produtividade da equipe de auditoria.")