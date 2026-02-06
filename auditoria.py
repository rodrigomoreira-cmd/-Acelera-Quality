import streamlit as st
import pandas as pd
from datetime import datetime

# IMPORTAÇÃO CORRETA: Usando a função com cache
from database import get_all_records_db

def render_auditoria():
    # 1. Trava de Segurança
    if st.session_state.get('nivel') != "ADMIN":
        st.error("🔒 Acesso negado. Apenas administradores podem visualizar os logs.")
        return

    st.title("🕵️ Painel de Auditoria")
    st.markdown("Rastreamento de ações sensíveis (Login, Monitorias, Exclusões, Alterações de Senha).")

    # 2. Botão de Atualização (Necessário por causa do Cache)
    if st.button("🔄 Atualizar Logs Agora"):
        get_all_records_db.clear()
        st.rerun()

    try:
        # 3. Busca os dados usando a função centralizada
        df = get_all_records_db("auditoria")
        
        if df is not None and not df.empty:
            # Tratamento de Data (Prioriza data_evento, fall back para criado_em)
            coluna_data = 'data_evento' if 'data_evento' in df.columns else 'criado_em'
            
            # Converte para datetime para ordenar corretamente
            df[coluna_data] = pd.to_datetime(df[coluna_data])
            df = df.sort_values(by=coluna_data, ascending=False)
            
            # Cria coluna formatada para exibição (BR)
            df['Data_Formatada'] = df[coluna_data].dt.strftime('%d/%m/%Y %H:%M:%S')

            # 4. Filtros Dinâmicos
            with st.expander("🔍 Filtros Avançados", expanded=True):
                c1, c2, c3 = st.columns(3)
                
                # Filtro: Quem fez?
                admins = ["Todos"] + sorted(df['admin_responsavel'].astype(str).unique().tolist())
                admin_sel = c1.selectbox("Executor (Admin):", admins)
                
                # Filtro: O que fez?
                acoes = ["Todas"] + sorted(df['acao'].astype(str).unique().tolist())
                acao_sel = c2.selectbox("Tipo de Ação:", acoes)
                
                # Filtro: Quem sofreu a ação?
                # Tratamento para remover valores nulos/None antes de ordenar
                lista_afetados = df['colaborador_afetado'].dropna().astype(str).unique().tolist()
                afetados = ["Todos"] + sorted(lista_afetados)
                afetado_sel = c3.selectbox("Colaborador Alvo:", afetados)

            # 5. Aplicação dos Filtros
            df_filt = df.copy()
            
            if admin_sel != "Todos":
                df_filt = df_filt[df_filt['admin_responsavel'] == admin_sel]
            
            if acao_sel != "Todas":
                df_filt = df_filt[df_filt['acao'] == acao_sel]
            
            if afetado_sel != "Todos":
                df_filt = df_filt[df_filt['colaborador_afetado'] == afetado_sel]

            # 6. Exibição da Tabela
            st.divider()
            st.markdown(f"**Registros encontrados:** `{len(df_filt)}`")
            
            # Prepara colunas para exibição limpa
            df_view = df_filt[['Data_Formatada', 'acao', 'admin_responsavel', 'colaborador_afetado', 'detalhes']].copy()
            df_view.columns = ['Data/Hora', 'Ação', 'Executor', 'Alvo', 'Detalhes']

            st.dataframe(
                df_view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Data/Hora": st.column_config.TextColumn("Horário (BR)", width="medium"),
                    "Ação": st.column_config.TextColumn("Ação", width="medium"),
                    "Executor": st.column_config.TextColumn("Resp.", width="small"),
                    "Alvo": st.column_config.TextColumn("Afetado", width="small"),
                    "Detalhes": st.column_config.TextColumn("Descrição Completa", width="large"),
                }
            )

            # 7. Exportação CSV
            csv = df_view.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Relatório (CSV)",
                data=csv,
                file_name=f'auditoria_log_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
                mime='text/csv'
            )

        else:
            st.info("📭 Nenhum registro de auditoria encontrado.")

    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")