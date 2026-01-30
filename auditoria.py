import streamlit as st
from datetime import datetime
import pandas as pd
from database import supabase

def render_auditoria():
    # 1. Trava de Segurança
    # Garante que apenas usuários com nível ADMIN acessem esta área sensível
    if st.session_state.get('nivel') != "ADMIN":
        st.error("Acesso negado. Apenas administradores podem visualizar os logs do sistema.")
        return

    st.title("🕵️ Painel de Auditoria")
    st.markdown("Acompanhe todas as ações críticas realizadas no sistema para garantir a integridade dos dados.")

    try:
        # 2. Busca os dados da tabela auditoria ordenados por data
        res = supabase.table("auditoria").select("*").order("criado_em", desc=True).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)

            # 3. Tratamento de Data com Pandas
            df['criado_em'] = pd.to_datetime(df['criado_em'])
            df['📅 Data/Hora'] = df['criado_em'].dt.strftime('%d/%m/%Y %H:%M:%S')

            # 4. Filtros Dinâmicos no Topo
            with st.expander("🔍 Filtros Avançados", expanded=True):
                c1, c2, c3 = st.columns(3)
                
                # Filtro por Responsável (Executor)
                admins = ["Todos"] + sorted(df['admin_responsavel'].unique().tolist())
                admin_sel = c1.selectbox("Quem realizou a ação:", admins)
                
                # Filtro por Tipo de Ação
                acoes = ["Todas"] + sorted(df['acao'].unique().tolist())
                acao_sel = c2.selectbox("Tipo de Ação:", acoes)
                
                # Filtro por Colaborador Afetado (Alvo)
                afetados = ["Todos"] + sorted(df['colaborador_afetado'].dropna().unique().tolist())
                afetado_sel = c3.selectbox("Colaborador afetado:", afetados)

            # 5. Aplicação Lógica dos Filtros
            df_filt = df.copy()
            if admin_sel != "Todos":
                df_filt = df_filt[df_filt['admin_responsavel'] == admin_sel]
            if acao_sel != "Todas":
                df_filt = df_filt[df_filt['acao'] == acao_sel]
            if afetado_sel != "Todos":
                df_filt = df_filt[df_filt['colaborador_afetado'] == afetado_sel]

            # 6. Exibição da Tabela Formatada
            st.divider()
            st.subheader(f"Registros Encontrados ({len(df_filt)})")
            
            # Preparação da visualização amigável
            df_view = df_filt[['📅 Data/Hora', 'admin_responsavel', 'acao', 'colaborador_afetado', 'detalhes']]
            df_view.columns = ['Data/Hora', 'Executor', 'Ação', 'Alvo', 'Detalhes']

            # Renderização com controle de largura de colunas
            st.dataframe(
                df_view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Detalhes": st.column_config.TextColumn("Detalhes da Operação", width="large"),
                    "Data/Hora": st.column_config.TextColumn("Momento", width="medium"),
                    "Ação": st.column_config.TextColumn("Tipo"),
                    "Executor": st.column_config.TextColumn("Admin Responsável")
                }
            )

            # 7. Opção de Exportação para Conformidade
            st.download_button(
                label="📥 Exportar Logs para CSV",
                data=df_view.to_csv(index=False).encode('utf-8'),
                file_name=f'auditoria_acelera_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                help="Baixe os logs filtrados para arquivamento ou análise externa."
            )

        else:
            st.info("Nenhum registro de auditoria encontrado até o momento.")

    except Exception as e:
        st.error(f"Erro técnico ao carregar os logs de auditoria: {e}")