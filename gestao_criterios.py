import streamlit as st
import pandas as pd
# IMPORTANTE: registrar_auditoria adicionado aqui!
from database import supabase, registrar_auditoria

def render_gestao_criterios():
    st.title("⚙️ Configuração de Critérios")
    st.markdown("Gerencie as perguntas que aparecem no checklist da monitoria.")

    # --- DEFINIÇÃO DAS CATEGORIAS ---
    OPCOES_CATEGORIAS = [
        "Nectar CRM",
        "Ambos - Processo SDR",
        "Identificar - Processo",
        "Integração",
        "Selene/Bot"
    ]
    
    # --- OPÇÕES DE DEPARTAMENTO ---
    OPCOES_DEPARTAMENTO = [
        "SDR",
        "Especialista",
        "Venda de Ingresso",
        "Auditor"
    ]

    # --- 1. ADICIONAR NOVO CRITÉRIO ---
    with st.expander("➕ Adicionar Novo Critério", expanded=False):
        with st.form("novo_item_form", clear_on_submit=True):
            st.markdown("### Novo Item")
            
            c_nome, c_grupo, c_dept = st.columns([3, 1.5, 1.5])
            nome = c_nome.text_input("Pergunta / Critério", placeholder="Ex: Preencheu o campo corretamente?")
            
            grupo = c_grupo.selectbox("Categoria", OPCOES_CATEGORIAS)
            departamento = c_dept.selectbox("Departamento", OPCOES_DEPARTAMENTO)
            
            c_peso, c_submit = st.columns([1, 1])
            peso = c_peso.number_input("Peso na Nota", min_value=1, max_value=100, value=1, step=1)
            
            c_submit.write("") 
            c_submit.write("") 
            
            if c_submit.form_submit_button("💾 Salvar Critério", use_container_width=True, type="primary"):
                if nome:
                    try:
                        payload = {
                            "nome_criterio": nome, 
                            "grupo": grupo,
                            "departamento": departamento, 
                            "peso": int(peso),
                            "ativo": True
                        }
                        supabase.table("config_criterios").insert(payload).execute()
                        
                        # --- 📸 LOG GRAVANDO CRIAÇÃO DO CRITÉRIO ---
                        registrar_auditoria(
                            acao="CRIAR CRITÉRIO",
                            detalhes=f"Criou o critério '{nome}' para a equipe '{departamento}' com peso {int(peso)}."
                        )
                        
                        st.toast(f"✅ Item adicionado para {departamento}: {nome}", icon="✨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("⚠️ O nome do critério é obrigatório.")

    st.divider()

    # --- 2. EDITOR EM MASSA ---
    st.subheader("📝 Editar Itens Ativos")
    
    try:
        res = supabase.table("config_criterios").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar critérios: {e}")
        df = pd.DataFrame()
    
    if not df.empty:
        colunas_necessarias = ['id', 'departamento', 'grupo', 'nome_criterio', 'peso', 'ativo']
        
        cols_existentes = [c for c in colunas_necessarias if c in df.columns]
        df_safe = df[cols_existentes].copy()
        
        if 'peso' in df_safe.columns:
            df_safe['peso'] = pd.to_numeric(df_safe['peso'], errors='coerce').fillna(1).astype('Int64')
        if 'id' in df_safe.columns:
            df_safe['id'] = pd.to_numeric(df_safe['id'], errors='coerce').astype('Int64')

        if 'departamento' in df_safe.columns:
            df_safe = df_safe.sort_values(by=['departamento', 'grupo'])
        elif 'grupo' in df_safe.columns:
            df_safe = df_safe.sort_values(by=['grupo'])

        df_editado = st.data_editor(
            df_safe,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "departamento": st.column_config.SelectboxColumn(
                    "Departamento",
                    width="small",
                    options=OPCOES_DEPARTAMENTO,
                    required=True
                ),
                "grupo": st.column_config.SelectboxColumn(
                    "Categoria",
                    width="medium",
                    options=OPCOES_CATEGORIAS,
                    required=True
                ),
                "nome_criterio": st.column_config.TextColumn("Pergunta do Checklist", width="large", required=True),
                "peso": st.column_config.NumberColumn("Peso", min_value=1, max_value=100, step=1, required=True),
                "ativo": st.column_config.CheckboxColumn("Ativo?")
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
                        peso_bruto = row.get("peso")
                        peso_seguro = int(float(str(peso_bruto))) if pd.notna(peso_bruto) else 1
                        
                        if pd.notna(row.get('id')):
                            id_seguro = int(float(str(row["id"])))
                            
                            payload_update = {
                                "nome_criterio": str(row["nome_criterio"]),
                                "grupo": str(row["grupo"]),
                                "peso": peso_seguro,
                                "ativo": bool(row["ativo"])
                            }
                            if 'departamento' in row:
                                payload_update['departamento'] = str(row['departamento'])

                            supabase.table("config_criterios").update(payload_update).eq("id", id_seguro).execute()
                            
                        elif pd.isna(row.get('id')) and row.get('nome_criterio'):
                            payload_insert = {
                                "nome_criterio": str(row["nome_criterio"]),
                                "grupo": str(row["grupo"]),
                                "peso": peso_seguro,
                                "ativo": bool(row.get("ativo", True))
                            }
                            if 'departamento' in row:
                                payload_insert['departamento'] = str(row['departamento'])
                            else:
                                payload_insert['departamento'] = "SDR"

                            supabase.table("config_criterios").insert(payload_insert).execute()
                    
                    # --- 📸 LOG GRAVANDO ALTERAÇÃO EM MASSA ---
                    registrar_auditoria(
                        acao="EDIÇÃO DE CRITÉRIOS",
                        detalhes="O gestor atualizou ou adicionou critérios através da tabela de edição em massa."
                    )
                    
                    st.toast("✅ Configurações atualizadas com sucesso!", icon="💾")
                    import time
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")

    else:
        st.info("Nenhum critério encontrado. Adicione o primeiro item acima!")