import streamlit as st
import pandas as pd
from database import supabase

def render_auditoria():
    st.title("🕵️ Painel de Auditoria")
    st.markdown("Rastreie todas as alterações críticas realizadas por administradores no sistema.")

    try:
        # 1. Busca os registros do banco (Tabela auditoria)
        res = supabase.table("auditoria").select("*").order("data_hora", desc=True).execute()
        
        if res.data:
            df_auditoria = pd.DataFrame(res.data)

            # --- SEÇÃO DE FILTROS ---
            with st.container(border=True):
                c1, c2 = st.columns(2)
                
                # Filtro por Responsável (Admin que executou a ação)
                admins = sorted(df_auditoria['admin_responsavel'].unique().tolist())
                admin_sel = c1.selectbox("🔍 Filtrar por Administrador:", ["Todos"] + admins)

                # Filtro por Tipo de Ação
                acoes = sorted(df_auditoria['acao'].unique().tolist())
                acao_sel = c2.selectbox("⚡ Filtrar por Tipo de Ação:", ["Todas"] + acoes)

            # --- APLICAÇÃO DA LÓGICA DE FILTRO ---
            df_filtrado = df_auditoria.copy()
            if admin_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado['admin_responsavel'] == admin_sel]
            if acao_sel != "Todas":
                df_filtrado = df_filtrado[df_filtrado['acao'] == acao_sel]

            # --- FORMATAÇÃO DE DADOS ---
            # Converte para datetime e formata para o padrão brasileiro
            df_filtrado['data_hora'] = pd.to_datetime(df_filtrado['data_hora']).dt.strftime('%d/%m/%Y %H:%M:%S')

            st.divider()

            # --- EXIBIÇÃO DA TABELA (ESTILIZADA) ---
            st.dataframe(
                df_filtrado, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "data_hora": st.column_config.TextColumn("📅 Data/Hora", width="medium"),
                    "admin_responsavel": "👤 Responsável",
                    "colaborador_afetado": "🎯 Colaborador Afetado",
                    "acao": "Ação Realizada",
                    "detalhes": st.column_config.TextColumn("📝 Detalhes da Mudança", width="large")
                }
            )

            st.caption(f"📌 Total de {len(df_filtrado)} registros encontrados com os filtros atuais.")

        else:
            st.info("💡 O histórico de auditoria está vazio no momento.")

    except Exception as e:
        st.error(f"❌ Erve um erro ao carregar os dados: {str(e)}")

# --- BARRA LATERAL INFORMATIVA ---
with st.sidebar:
    st.divider()
    st.info("""
    **🛡️ Segurança e Auditoria**
    
    Este log registra ações críticas:
    * **CADASTRO:** Inclusão de novos SDRs ou ADMs.
    * **ALTERAÇÃO:** Edição de nomes ou dados.
    * **STATUS:** Ativação ou Bloqueio de contas.
    * **SENHA:** Resets efetuados pela gestão.
    """)