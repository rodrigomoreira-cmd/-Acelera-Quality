import streamlit as st
import pandas as pd
from database import supabase

def render_gestao_criterios():
    st.title("⚙️ Configuração de Critérios")
    st.markdown("Gerencie as perguntas que aparecem no checklist da monitoria.")

    # --- DEFINIÇÃO DAS CATEGORIAS (Conforme sua imagem) ---
    OPCOES_CATEGORIAS = [
        "Nectar CRM",
        "Ambos - Processo SDR",
        "Identificar - Processo",
        "Integração",
        "Selene/Bot"
    ]

    # --- 1. ADICIONAR NOVO CRITÉRIO ---
    with st.expander("➕ Adicionar Novo Critério", expanded=False):
        with st.form("novo_item_form", clear_on_submit=True):
            st.markdown("### Novo Item")
            
            c_nome, c_grupo = st.columns([3, 1.5])
            nome = c_nome.text_input("Pergunta / Critério", placeholder="Ex: Preencheu o campo corretamente?")
            
            # Usa a lista definida acima
            grupo = c_grupo.selectbox("Categoria", OPCOES_CATEGORIAS)
            
            c_peso, c_submit = st.columns([1, 1])
            peso = c_peso.number_input("Peso na Nota", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
            
            c_submit.write("") 
            c_submit.write("") 
            
            if c_submit.form_submit_button("💾 Salvar Critério", use_container_width=True, type="primary"):
                if nome:
                    try:
                        payload = {
                            "nome_criterio": nome, 
                            "grupo": grupo,
                            "peso": peso,
                            "ativo": True
                        }
                        supabase.table("config_criterios").insert(payload).execute()
                        st.toast(f"✅ Item adicionado: {nome}", icon="✨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("⚠️ O nome do critério é obrigatório.")

    st.divider()

    # --- 2. EDITOR EM MASSA ---
    st.subheader("📝 Editar Itens Ativos")
    
    try:
        # Busca direta ordenando por ID para evitar erro de data
        res = supabase.table("config_criterios").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar critérios: {e}")
        df = pd.DataFrame()
    
    if not df.empty:
        # Prepara o DataFrame para exibição
        colunas_necessarias = ['id', 'grupo', 'nome_criterio', 'peso', 'ativo']
        
        # Filtra colunas se existirem
        cols_existentes = [c for c in colunas_necessarias if c in df.columns]
        df_safe = df[cols_existentes].copy()
        
        if 'grupo' in df_safe.columns:
            df_safe = df_safe.sort_values(by=['grupo'])

        df_editado = st.data_editor(
            df_safe,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "grupo": st.column_config.SelectboxColumn(
                    "Categoria",
                    width="medium",
                    # Atualizado com as novas categorias
                    options=OPCOES_CATEGORIAS,
                    required=True
                ),
                "nome_criterio": st.column_config.TextColumn("Pergunta do Checklist", width="large", required=True),
                "peso": st.column_config.NumberColumn("Peso", min_value=0.1, max_value=10.0, format="%.1f"),
                "ativo": st.column_config.CheckboxColumn("Ativo?", help="Desmarque para esconder")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )

        st.caption("💡 Dica: Edite diretamente na tabela e clique em salvar abaixo.")

        if st.button("🔄 Aplicar Alterações em Massa", type="primary", use_container_width=True):
            with st.spinner("Atualizando banco de dados..."):
                try:
                    for index, row in df_editado.iterrows():
                        # Update seguro usando ID
                        if pd.notna(row.get('id')):
                            supabase.table("config_criterios").update({
                                "nome_criterio": row["nome_criterio"],
                                "grupo": row["grupo"],
                                "peso": row["peso"],
                                "ativo": row["ativo"]
                            }).eq("id", int(row["id"])).execute()
                        # Se não tiver ID (linha nova adicionada pelo editor), insere
                        elif pd.isna(row.get('id')) and row.get('nome_criterio'):
                            supabase.table("config_criterios").insert({
                                "nome_criterio": row["nome_criterio"],
                                "grupo": row["grupo"],
                                "peso": row["peso"],
                                "ativo": row.get("ativo", True)
                            }).execute()
                    
                    st.toast("✅ Configurações atualizadas!", icon="💾")
                    import time
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")

    else:
        st.info("Nenhum critério encontrado. Adicione o primeiro item acima!")