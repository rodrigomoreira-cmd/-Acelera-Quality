import streamlit as st
import pandas as pd
from database import supabase, get_all_records_db

def render_gestao_criterios():
    st.title("⚙️ Gestão de Itens da Monitoria")

    # 1. Adicionar Novo Critério
    with st.expander("➕ Adicionar Novo Critério"):
        with st.form("novo_item_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            nome = col1.text_input("Nome do Critério", placeholder="Ex: Fez a saudação inicial?")
            # Adicionando Grupo e Peso no formulário
            grupo = col2.selectbox("Grupo", ["Saudação", "Investigação", "Pitch", "Fechamento", "Processo CRM"])
            peso = col3.number_input("Peso", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
            
            if st.form_submit_button("Salvar"):
                if nome:
                    try:
                        payload = {
                            "nome_criterio": nome, 
                            "grupo": grupo,
                            "peso": peso,
                            "ativo": True
                        }
                        supabase.table("config_criterios").insert(payload).execute()
                        st.success(f"Critério '{nome}' adicionado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    st.divider()

    # 2. Editar Itens Existentes
    st.subheader("📝 Itens Cadastrados")
    df = get_all_records_db("config_criterios")
    
    if not df.empty:
        # Garantimos que as colunas peso e grupo estão no DataFrame
        # Se as colunas não existirem no banco, o código abaixo pode precisar de ajuste SQL
        colunas_necessarias = ['id', 'nome_criterio', 'grupo', 'peso', 'ativo']
        
        # Filtramos apenas as colunas que queremos editar
        df_edit = st.data_editor(
            df[colunas_necessarias],
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "nome_criterio": st.column_config.TextColumn("Critério", width="large"),
                "grupo": st.column_config.SelectboxColumn("Grupo", options=["Saudação", "Investigação", "Pitch", "Fechamento", "Processo CRM"]),
                "peso": st.column_config.NumberColumn("Peso (Pontuação)", min_value=0.1, max_value=5.0, format="%.1f"),
                "ativo": st.column_config.CheckboxColumn("Ativo?")
            },
            use_container_width=True, 
            hide_index=True
        )
        
        if st.button("💾 Aplicar Alterações"):
            try:
                for _, row in df_edit.iterrows():
                    supabase.table("config_criterios").update({
                        "nome_criterio": row["nome_criterio"],
                        "grupo": row["grupo"],
                        "peso": row["peso"],
                        "ativo": row["ativo"]
                    }).eq("id", row["id"]).execute()
                st.success("Configurações atualizadas!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")