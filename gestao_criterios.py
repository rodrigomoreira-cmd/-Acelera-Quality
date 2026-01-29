import streamlit as st
import pandas as pd
from database import supabase, get_all_records_db

def render_gestao_criterios():
    st.title("⚙️ Gestão de Itens da Monitoria")

    # Adicionar Novo Critério
    with st.expander("➕ Adicionar Novo Critério"):
        with st.form("novo_item_form"):
            nome = st.text_input("Nome do Critério (Ex: Saudação)")
            if st.form_submit_button("Salvar"):
                if nome:
                    supabase.table("config_criterios").insert({"nome_criterio": nome, "ativo": True}).execute()
                    st.success(f"Critério '{nome}' adicionado!")
                    st.rerun()

    st.divider()

    # Editar Itens Existentes
    st.subheader("📝 Itens Cadastrados")
    df = get_all_records_db("config_criterios")
    
    if not df.empty:
        # Colunas baseadas na sua imagem: id, nome_criterio, ativo
        df_edit = st.data_editor(
            df[['id', 'nome_criterio', 'ativo']],
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "ativo": st.column_config.CheckboxColumn("Ativo?")
            },
            use_container_width=True, hide_index=True
        )
        
        if st.button("💾 Aplicar Alterações"):
            for _, row in df_edit.iterrows():
                supabase.table("config_criterios").update({
                    "nome_criterio": row["nome_criterio"],
                    "ativo": row["ativo"]
                }).eq("id", row["id"]).execute()
            st.success("Configurações atualizadas!")
            st.rerun()