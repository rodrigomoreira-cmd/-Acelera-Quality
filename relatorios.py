import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
from database import get_all_records_db, supabase

def render_relatorios():
    st.title("📊 Relatório Executivo (BI)")
    st.markdown("Acompanhe os KPIs da equipe, tendências de notas e exporte a base consolidada.")

    # 1. Recupera contexto de acesso
    nivel = st.session_state.get('nivel', 'USUARIO')
    dept_logado = st.session_state.get('departamento_selecionado', 'Todos')

    # 2. Busca os dados brutos
    df_mon = get_all_records_db("monitorias")
    df_cont = get_all_records_db("contestacoes")
    df_comp = get_all_records_db("avaliacoes_comportamentais")

    if df_mon is None or df_mon.empty:
        st.warning("Não há dados de monitoria suficientes para gerar relatórios.")
        return

    # =========================================================
    # 🛡️ TRAVAS DE SEGURANÇA E VISIBILIDADE
    # =========================================================
    # Oculta o Admin Mestre para não-admins
    if nivel != "ADMIN":
        df_mon = df_mon[
            (df_mon['sdr'] != 'admin@grupoacelerador.com.br') & 
            (df_mon['monitor_responsavel'] != 'admin@grupoacelerador.com.br')
        ]
        if df_comp is not None and not df_comp.empty:
            df_comp = df_comp[df_comp['sdr_nome'] != 'admin@grupoacelerador.com.br']

    # Filtra pelo Departamento selecionado na barra lateral
    if dept_logado != "Todos" and 'departamento' in df_mon.columns:
        df_mon = df_mon[df_mon['departamento'].str.upper() == dept_logado.upper()]
        if df_comp is not None and not df_comp.empty and 'departamento' in df_comp.columns:
            df_comp = df_comp[df_comp['departamento'].str.upper() == dept_logado.upper()]

    if df_mon.empty:
        st.info(f"Nenhum registro encontrado para o departamento: **{dept_logado}**.")
        return

    # =========================================================
    # 🕵️ ÁREA DE FILTROS (SDR e DATA)
    # =========================================================
    with st.container(border=True):
        st.markdown("#### 🔍 Filtros de Análise")
        col_f1, col_f2 = st.columns(2)
        
        # Filtro 1: Seleção de SDR
        with col_f1:
            lista_sdrs = sorted(list(df_mon['sdr'].dropna().unique()))
            sdr_selecionado = st.selectbox("👤 Filtrar por Colaborador:", ["Todos da Equipe"] + lista_sdrs)

        # Filtro 2: Seleção de Data
        with col_f2:
            hoje = datetime.now().date()
            inicio_mes = hoje.replace(day=1)
            periodo = st.date_input("📅 Período de Análise:", value=(inicio_mes, hoje), format="DD/MM/YYYY")

    # =========================================================
    # ⚙️ APLICAÇÃO DOS FILTROS
    # =========================================================
    df_mon['criado_em'] = pd.to_datetime(df_mon['criado_em'])
    df_mon['data_filtro'] = df_mon['criado_em'].dt.date
    
    # 1. Filtra SDR
    if sdr_selecionado != "Todos da Equipe":
        df_mon = df_mon[df_mon['sdr'] == sdr_selecionado]
        if df_comp is not None and not df_comp.empty:
            df_comp = df_comp[df_comp['sdr_nome'] == sdr_selecionado]

    # 2. Filtra Data
    meses_selecionados = []
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
        df_mon = df_mon[(df_mon['data_filtro'] >= inicio) & (df_mon['data_filtro'] <= fim)]
        # Mapeia os meses do período para filtrar o PDI (ex: '02/2026')
        meses_selecionados = pd.date_range(inicio, fim, freq='MS').strftime("%m/%Y").tolist()
        if inicio.strftime("%m/%Y") not in meses_selecionados:
            meses_selecionados.append(inicio.strftime("%m/%Y"))
    elif isinstance(periodo, tuple) and len(periodo) == 1:
        df_mon = df_mon[df_mon['data_filtro'] == periodo[0]]
        meses_selecionados = [periodo[0].strftime("%m/%Y")]

    if df_mon.empty:
        st.warning("Nenhum registro técnico encontrado neste período específico.")
        return

    # =========================================================
    # 📈 KPIs EXECUTIVOS (CARDS)
    # =========================================================
    qtd_monitorias = len(df_mon)
    media_qa = df_mon['nota'].mean()

    # Cálculo PDI
    media_pdi_pct = 0.0
    if df_comp is not None and not df_comp.empty and meses_selecionados:
        df_comp_filtrado = df_comp[df_comp['mes_referencia'].isin(meses_selecionados)]
        if not df_comp_filtrado.empty:
            media_pdi_bruta = df_comp_filtrado['media_comportamental'].astype(float).mean()
            media_pdi_pct = (media_pdi_bruta / 5.0) * 100

    # Cálculo Contestação
    taxa_contestacao = 0.0
    if 'contestada' in df_mon.columns:
        qtd_contestadas = len(df_mon[df_mon['contestada'] == True])
        taxa_contestacao = (qtd_contestadas / qtd_monitorias) * 100 if qtd_monitorias > 0 else 0

    st.markdown("### 🎯 Visão Geral de Performance")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Média de Qualidade (QA)", f"{media_qa:.1f}%")
    k2.metric("Média Comportamental (PDI)", f"{media_pdi_pct:.1f}%" if media_pdi_pct > 0 else "N/A")
    k3.metric("Total de Avaliações (Vol.)", qtd_monitorias)
    k4.metric("Taxa de Contestação", f"{taxa_contestacao:.1f}%")

    st.divider()

    # =========================================================
    # 📊 GRÁFICOS DE TENDÊNCIA
    # =========================================================
    st.markdown("### 📉 Evolução Técnica ao Longo do Tempo")
    
    # Agrupa notas por data
    df_tendencia = df_mon.groupby('data_filtro')['nota'].mean().reset_index()
    df_tendencia.rename(columns={'data_filtro': 'Data', 'nota': 'Média Diária'}, inplace=True)
    
    fig = px.line(
        df_tendencia, x="Data", y="Média Diária", 
        markers=True, 
        line_shape="spline", # Linha suave
        color_discrete_sequence=["#ff4b4b"]
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        font={'color': "white"},
        yaxis_title="Nota Técnica (%)",
        xaxis_title="Período",
        yaxis_range=[0, 105]
    )
    fig.update_traces(marker=dict(size=8, color="white", line=dict(width=2, color="#ff4b4b")))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================================================
    # 🔄 CRUZAMENTO DE DADOS (MONITORIA + CONTESTAÇÃO)
    # =========================================================
    st.markdown("### 📋 Base de Dados Consolidada")

    if df_cont is not None and not df_cont.empty:
        df_cont_resumo = df_cont[['monitoria_id', 'motivo', 'resposta_admin', 'status']].rename(columns={
            'motivo': 'Motivo Contestação',
            'resposta_admin': 'Resposta Gestão',
            'status': 'Status Contestação'
        })
        df_final = pd.merge(df_mon, df_cont_resumo, left_on='id', right_on='monitoria_id', how='left')
    else:
        df_final = df_mon.copy()
        df_final['Motivo Contestação'] = "-"
        df_final['Resposta Gestão'] = "-"
        df_final['Status Contestação'] = "-"

    # Função para extrair apenas NC e NCG
    def processar_erros(detalhes):
        if not detalhes or not isinstance(detalhes, dict): return ""
        erros = [f"{k} ({v})" for k, v in detalhes.items() if v in ["NC", "NCG", "NC Grave"]]
        return " | ".join(erros) if erros else ""

    try:
        df_final['Detalhes (Erros)'] = df_final['detalhes'].apply(processar_erros)
        df_final['Data Monitoria'] = df_final['criado_em'].dt.strftime('%d/%m/%Y %H:%M')
        df_final['Contestado'] = df_final['contestada'].apply(lambda x: "Sim" if x else "Não")
        
        cols_fillna = ['Motivo Contestação', 'Resposta Gestão', 'Status Contestação']
        for c in cols_fillna: 
            if c in df_final.columns: df_final[c] = df_final[c].fillna("-")

        colunas_ordenadas = [
            'Data Monitoria', 'sdr', 'nota', 'monitor_responsavel', 
            'Contestado', 'Status Contestação', 'Detalhes (Erros)', 
            'observacoes', 'link_selene', 'link_nectar'
        ]
        
        cols_existentes = [c for c in colunas_ordenadas if c in df_final.columns]
        df_export = df_final[cols_existentes].copy()

        mapa_renomeacao = {
            'sdr': 'Colaborador',
            'nota': 'Nota Final (%)',
            'observacoes': 'Feedback Geral',
            'monitor_responsavel': 'Avaliador',
            'link_selene': 'Link Selene',
            'link_nectar': 'Link CRM'
        }
        df_export.rename(columns=mapa_renomeacao, inplace=True)

        # =========================================================
        # 👁️ PRÉVIA E DOWNLOAD
        # =========================================================
        st.dataframe(
            df_export,
            column_config={
                "Link Selene": st.column_config.LinkColumn("Gravação"),
                "Link CRM": st.column_config.LinkColumn("Card CRM"),
                "Nota Final (%)": st.column_config.ProgressColumn("Nota (%)", format="%d%%", min_value=0, max_value=100)
            },
            hide_index=True,
            use_container_width=True,
            height=250
        )
        
        st.write("##")
        c_vazio, c_btn, c_vazio2 = st.columns([1, 2, 1]) 
        with c_btn:
            csv = df_export.to_csv(sep=';', index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 BAIXAR BASE EM EXCEL (.CSV)",
                data=csv,
                file_name=f"BI_Qualidade_{dept_logado}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

    except Exception as e:
        st.error(f"Erro ao gerar a tabela de exportação: {e}")