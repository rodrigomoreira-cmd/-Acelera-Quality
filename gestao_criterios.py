import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria
import time

def render_gestao_criterios():
    st.title("⚙️ Configuração de Critérios")
    st.markdown("Gerencie as perguntas do checklist de monitoria (com pesos e travas) e as competências do PDI.")

    # Listas globais para as duas abas
    OPCOES_CATEGORIAS = ["Nectar CRM", "Ambos - Processo SDR", "Identificar - Processo", "Integração", "Selene/Bot"]
    OPCOES_DEPARTAMENTO = ["SDR", "Especialista", "Venda de Ingresso", "Auditor", "Todos"]

    aba_qa, aba_pdi = st.tabs(["🎧 Critérios de Qualidade (QA)", "🎯 Critérios Comportamentais (PDI)"])

    # ==========================================================
    # ABA 1: CRITÉRIOS DE QUALIDADE (QA) - COM PESOS E FATAL
    # ==========================================================
    with aba_qa:
        # --- 1. FORMULÁRIO DE ADIÇÃO ---
        with st.expander("➕ Adicionar Novo Critério QA (Com Peso/Fatal)", expanded=False):
            with st.form("novo_item_qa_form", clear_on_submit=True):
                st.markdown("### Novo Item de Avaliação")
                
                nome = st.text_input("Pergunta / Critério", placeholder="Ex: Confirmou os dados de contato?")
                
                c_grupo, c_dept = st.columns(2)
                grupo = c_grupo.selectbox("Categoria", OPCOES_CATEGORIAS)
                departamento = c_dept.selectbox("Departamento Destino", OPCOES_DEPARTAMENTO)
                
                st.divider()
                st.markdown("#### ⚖️ Inteligência do Critério")
                col_p, col_f = st.columns([2, 1])
                
                peso = col_p.select_slider(
                    "Peso do Item (Importância)",
                    options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    value=1,
                    help="Quanto maior o peso, maior o impacto na nota se for marcado como Não Conforme."
                )
                
                eh_fatal = col_f.checkbox(
                    "🔴 ITEM FATAL", 
                    help="⚠️ ATENÇÃO: Se o colaborador for avaliado como 'NC' neste item, a nota será 0 AUTOMATICAMENTE."
                )
                
                desc_ajuda = st.text_area("Guia para o Auditor (O que observar?)", placeholder="Descreva aqui o que valida este item como Conforme.")

                if st.form_submit_button("💾 Salvar Critério QA", use_container_width=True, type="primary"):
                    if nome:
                        try:
                            payload = {
                                "nome": nome, 
                                "descricao": desc_ajuda,
                                "grupo": grupo, 
                                "departamento": departamento, 
                                "peso": int(peso), 
                                "eh_fatal": bool(eh_fatal),
                                "esta_ativo": True
                            }
                            supabase.table("criterios_qa").insert(payload).execute()
                            
                            registrar_auditoria(
                                acao="CRIAR CRITÉRIO QA", 
                                detalhes=f"Criou critério '{nome}' (Peso: {peso}, Fatal: {eh_fatal})"
                            )
                            
                            st.toast(f"✅ Critério adicionado!", icon="✨")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}")
                    else: 
                        st.warning("⚠️ O nome do critério é obrigatório.")

        st.divider()

        # --- 2. EDITOR EM MASSA (QA) ---
        st.subheader("📝 Gerenciar e Editar Critérios Ativos")
        try:
            res = supabase.table("criterios_qa").select("*").order("grupo", desc=False).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Erro ao buscar: {e}")
            df = pd.DataFrame()
        
        if not df.empty:
            df_editado = st.data_editor(
                df[['id', 'grupo', 'nome', 'peso', 'eh_fatal', 'esta_ativo', 'departamento']],
                column_config={
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "grupo": st.column_config.SelectboxColumn("Categoria", options=OPCOES_CATEGORIAS, required=True),
                    "nome": st.column_config.TextColumn("Critério / Pergunta", width="large", required=True),
                    "peso": st.column_config.NumberColumn("Peso", min_value=1, max_value=10, step=1),
                    "eh_fatal": st.column_config.CheckboxColumn("🚨 Fatal?"),
                    "esta_ativo": st.column_config.CheckboxColumn("Ativo?"),
                    "departamento": st.column_config.SelectboxColumn("Dept", options=OPCOES_DEPARTAMENTO)
                },
                hide_index=True, 
                use_container_width=True,
                num_rows="dynamic"
            )

            if st.button("🔄 Aplicar Alterações em Massa (QA)", type="primary", use_container_width=True):
                with st.spinner("Sincronizando com o banco de dados..."):
                    try:
                        for _, row in df_editado.iterrows():
                            if pd.notna(row.get('id')):
                                upd_payload = {
                                    "nome": str(row["nome"]),
                                    "grupo": str(row["grupo"]),
                                    "peso": int(row["peso"]),
                                    "eh_fatal": bool(row["eh_fatal"]),
                                    "esta_ativo": bool(row["esta_ativo"]),
                                    "departamento": str(row["departamento"])
                                }
                                supabase.table("criterios_qa").update(upd_payload).eq("id", row["id"]).execute()
                        
                        registrar_auditoria("EDIÇÃO EM MASSA QA", "Atualizou pesos e status dos critérios.")
                        st.toast("✅ Base de critérios atualizada!", icon="💾")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Erro na atualização: {e}")
        else:
            st.info("Nenhum critério cadastrado na tabela 'criterios_qa'.")

    # ==========================================================
    # ABA 2: CRITÉRIOS COMPORTAMENTAIS (PDI)
    # ==========================================================
    with aba_pdi:
        with st.expander("➕ Adicionar Nova Soft Skill (PDI)", expanded=False):
            with st.form("novo_pdi_form", clear_on_submit=True):
                st.markdown("### Nova Competência Comportamental")
                
                # --- MELHORIA: ADICIONADO FILTRO DE DEPARTAMENTO AQUI ---
                c_nome_pdi, c_dept_pdi = st.columns([2, 1])
                nome_pdi = c_nome_pdi.text_input("Nome da Soft Skill", placeholder="Ex: Inteligência Emocional")
                dept_pdi = c_dept_pdi.selectbox("Departamento", OPCOES_DEPARTAMENTO, index=len(OPCOES_DEPARTAMENTO)-1) # Padrão "Todos"
                
                desc_pdi = st.text_input("Descrição Curta", placeholder="Como o gestor deve avaliar?")
                
                if st.form_submit_button("💾 Salvar Competência PDI", type="primary"):
                    if nome_pdi:
                        try:
                            # --- MELHORIA: PAYLOAD AGORA SALVA O DEPARTAMENTO ---
                            payload_pdi = {
                                "nome": nome_pdi.strip(), 
                                "descricao": desc_pdi.strip(), 
                                "departamento": dept_pdi, 
                                "esta_ativo": True
                            }
                            supabase.table("criterios_comportamentais").insert(payload_pdi).execute()
                            registrar_auditoria("CRIAR CRITÉRIO PDI", f"Adicionou Skill: {nome_pdi}")
                            st.toast(f"✅ Skill adicionada!", icon="🎯")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                    else: st.warning("⚠️ Nome obrigatório.")

        st.divider()
        st.subheader("📝 Editar Competências do PDI")
        try:
            res_comp = supabase.table("criterios_comportamentais").select("*").order("nome").execute()
            df_comp = pd.DataFrame(res_comp.data) if res_comp.data else pd.DataFrame()
            
            if not df_comp.empty:
                # Caso a coluna departamento não exista no pandas por ser muito velha, criamos provisória
                if 'departamento' not in df_comp.columns:
                    df_comp['departamento'] = 'Todos'

                # --- MELHORIA: ADICIONADO 'DEPARTAMENTO' NO EDITOR EM MASSA ---
                df_edit_comp = st.data_editor(
                    df_comp[['id', 'nome', 'descricao', 'departamento', 'esta_ativo']],
                    column_config={
                        "id": st.column_config.TextColumn("ID", disabled=True),
                        "nome": st.column_config.TextColumn("Nome da Skill", required=True),
                        "departamento": st.column_config.SelectboxColumn("Dept", options=OPCOES_DEPARTAMENTO),
                        "esta_ativo": st.column_config.CheckboxColumn("Ativo?")
                    },
                    hide_index=True, use_container_width=True
                )

                if st.button("🔄 Salvar Alterações em Massa (PDI)", type="primary", use_container_width=True):
                    for _, r in df_edit_comp.iterrows():
                        if pd.notna(r.get('id')):
                            p_pdi = {
                                "nome": str(r["nome"]), 
                                "descricao": str(r.get("descricao", "")), 
                                "departamento": str(r.get("departamento", "Todos")),
                                "esta_ativo": bool(r["esta_ativo"])
                            }
                            supabase.table("criterios_comportamentais").update(p_pdi).eq("id", r["id"]).execute()
                    st.toast("✅ PDI Atualizado!")
                    time.sleep(1)
                    st.rerun()
        except Exception as e:
            st.info(f"Crie o primeiro critério de PDI acima. (Erro: {e})")