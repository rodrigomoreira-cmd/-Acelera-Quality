import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_all_records_db, supabase

def render_relatorios():
    st.title("📊 Relatório Consolidado")
    st.markdown("Filtre e exporte a base completa cruzando dados de **Monitoria** e **Contestação**.")

    # 1. Busca os dados brutos
    df_mon = get_all_records_db("monitorias")
    df_cont = get_all_records_db("contestacoes")

    if df_mon is None or df_mon.empty:
        st.warning("Não há dados de monitoria para gerar relatório.")
        return

    # =========================================================
    # 🕵️ ÁREA DE FILTROS (SDR e DATA)
    # =========================================================
    with st.container(border=True):
        col_f1, col_f2 = st.columns(2)
        
        # Filtro 1: Seleção de SDR
        with col_f1:
            lista_sdrs = sorted(list(df_mon['sdr'].unique()))
            sdr_selecionado = st.selectbox("👤 Filtrar por SDR:", ["Todos"] + lista_sdrs)

        # Filtro 2: Seleção de Data
        with col_f2:
            # Define datas padrão (Início do mês até hoje)
            hoje = datetime.now().date()
            inicio_mes = hoje.replace(day=1)
            
            periodo = st.date_input(
                "📅 Período de Análise:",
                value=(inicio_mes, hoje),
                format="DD/MM/YYYY"
            )

    # =========================================================
    # ⚙️ APLICAÇÃO DOS FILTROS
    # =========================================================
    
    # Prepara coluna de data para filtro
    df_mon['data_filtro'] = pd.to_datetime(df_mon['criado_em']).dt.date
    
    # 1. Filtra SDR
    if sdr_selecionado != "Todos":
        df_mon = df_mon[df_mon['sdr'] == sdr_selecionado]

    # 2. Filtra Data (Garante que o usuário selecionou início e fim)
    if isinstance(periodo, tuple) and len(periodo) == 2:
        inicio, fim = periodo
        df_mon = df_mon[
            (df_mon['data_filtro'] >= inicio) & 
            (df_mon['data_filtro'] <= fim)
        ]
    elif isinstance(periodo, tuple) and len(periodo) == 1:
        # Se selecionou só a data de início, filtra só por ela
        df_mon = df_mon[df_mon['data_filtro'] == periodo[0]]

    # Se após filtrar não sobrar nada, avisa e para
    if df_mon.empty:
        st.warning(f"Nenhum registro encontrado para os filtros selecionados.")
        return

    # =========================================================
    # 🔄 PROCESSAMENTO E CRUZAMENTO DE DADOS
    # =========================================================

    # Prepara DataFrame de Contestações
    if df_cont is not None and not df_cont.empty:
        df_cont = df_cont[['monitoria_id', 'motivo', 'resposta_admin', 'status']].rename(columns={
            'motivo': 'Motivo Contestação',
            'resposta_admin': 'Resposta Gestão',
            'status': 'Status Contestação'
        })
        # Left Join: Junta Monitoria + Contestação
        df_final = pd.merge(df_mon, df_cont, left_on='id', right_on='monitoria_id', how='left')
    else:
        df_final = df_mon.copy()
        df_final['Motivo Contestação'] = None
        df_final['Resposta Gestão'] = None
        df_final['Status Contestação'] = None

    # Função para extrair apenas NC e NCG
    def processar_erros(detalhes):
        if not detalhes or not isinstance(detalhes, dict):
            return ""
        # Filtra apenas o que não for "C" (Conforme) ou "NA"
        erros = [f"{k} ({v})" for k, v in detalhes.items() if v in ["NC", "NCG"]]
        return " | ".join(erros) if erros else ""

    try:
        # Aplica lógica de erro (NC/NCG)
        df_final['Detalhes (NC/NCG)'] = df_final['detalhes'].apply(processar_erros)
        
        # Formata Datas e Strings
        df_final['Data Monitoria'] = pd.to_datetime(df_final['criado_em']).dt.strftime('%d/%m/%Y %H:%M')
        df_final['Data Extração'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        df_final['Contestado'] = df_final['contestada'].apply(lambda x: "Sim" if x else "Não")
        df_final['Visualizada'] = df_final['visualizada'].apply(lambda x: "Sim" if x else "Não")
        
        # Preenche vazios
        cols_fillna = ['Motivo Contestação', 'Resposta Gestão', 'Status Contestação']
        df_final[cols_fillna] = df_final[cols_fillna].fillna("-")

        # Define a Ordem e Seleção EXATA das colunas
        colunas_ordenadas = [
            'id',                     
            'Data Monitoria',         
            'sdr',                    
            'nota',                   
            'observacoes',            
            'monitor_responsavel',    
            'Contestado',             
            'Motivo Contestação',     
            'Resposta Gestão',        
            'Status Contestação',     
            'Data Extração',          
            'Detalhes (NC/NCG)',      
            'link_selene',            
            'link_nectar',            
            'Visualizada'             
        ]
        
        # Garante que só pegamos colunas que existem (segurança)
        cols_existentes = [c for c in colunas_ordenadas if c in df_final.columns]
        df_export = df_final[cols_existentes].copy()

        # Renomeia para o Excel Final
        mapa_renomeacao = {
            'id': 'ID',
            'sdr': 'SDR',
            'nota': 'Nota Final',
            'observacoes': 'Observações',
            'monitor_responsavel': 'Monitor',
            'link_selene': 'Link Selene',
            'link_nectar': 'Link Néctar'
        }
        df_export.rename(columns=mapa_renomeacao, inplace=True)

        # =========================================================
        # 👁️ PRÉVIA E DOWNLOAD
        # =========================================================
        
        st.subheader(f"👁️ Prévia ({len(df_export)} registros)")
        st.dataframe(
            df_export,
            column_config={
                "Link Selene": st.column_config.LinkColumn("Link Selene"),
                "Link Néctar": st.column_config.LinkColumn("Link Néctar"),
            },
            hide_index=True,
            use_container_width=True,
            height=300
        )
        
        st.write("---")

        # Botão Centralizado
        c1, c2, c3 = st.columns([1, 2, 1]) 
        with c2:
            # Gera CSV (Separador ; para Excel BR)
            csv = df_export.to_csv(sep=';', index=False, encoding='utf-8-sig')
            
            st.download_button(
                label="📥 BAIXAR RELATÓRIO FILTRADO (EXCEL)",
                data=csv,
                file_name=f"Relatorio_Qualidade_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )

    except Exception as e:
        st.error(f"Erro ao processar relatório: {e}")