import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria
import time

def render_gestao_criterios():
    st.title("⚙️ Configuração de Critérios")
    st.markdown("Gerencie as perguntas do checklist de monitoria e competências do PDI.")

    usuario_logado = st.session_state.get('user_nome', 'Sistema')

    OPCOES_CATEGORIAS = ["Nectar CRM", "Ambos - Processo SDR", "Identificar - Processo", "Integração", "Selene/Bot"]
    OPCOES_DEPARTAMENTO = ["SDR", "Especialista", "Venda de Ingresso", "Auditor", "Todos"]

    # ==========================================================
    # MODIFICADO: A TERCEIRA ABA (LIDERANÇA) FOI COMENTADA E REMOVIDA DA VISÃO
    # ==========================================================
    # aba_qa, aba_pdi, aba_lid = st.tabs(["🎧 Critérios de Qualidade (QA)", "🎯 Competências PDI", "⬆️ Avaliação Liderança (360)"])
    aba_qa, aba_pdi = st.tabs(["🎧 Critérios de Qualidade (QA)", "🎯 Competências PDI"])

    # ==========================================================
    # ABA 1: CRITÉRIOS DE QUALIDADE (QA)
    # ==========================================================
    with aba_qa:
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
                peso = col_p.select_slider("Peso do Item", options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], value=1)
                eh_fatal = col_f.checkbox("🔴 ITEM FATAL")
                desc_ajuda = st.text_area("Guia para o Auditor")

                if st.form_submit_button("💾 Salvar Critério QA", use_container_width=True, type="primary"):
                    if nome:
                        try:
                            payload = {
                                "nome": nome, "descricao": desc_ajuda, "grupo": grupo, 
                                "departamento": departamento, "peso": int(peso), 
                                "eh_fatal": bool(eh_fatal), "esta_ativo": True
                            }
                            supabase.table("criterios_qa").insert(payload).execute()
                            registrar_auditoria("CRIAR CRITÉRIO QA", f"Criou critério '{nome}'", "Geral", usuario_logado)
                            st.toast(f"✅ Critério adicionado!", icon="✨")
                            time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Erro ao salvar: {e}")
                    else: st.warning("⚠️ O nome do critério é obrigatório.")

        st.divider()
        st.subheader("📝 Gerenciar e Editar Critérios Ativos")
        try:
            res = supabase.table("criterios_qa").select("*").order("grupo", desc=False).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Erro ao buscar: {e}"); df = pd.DataFrame()
        
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
                hide_index=True, use_container_width=True, num_rows="dynamic"
            )

            if st.button("🔄 Aplicar Alterações em Massa (QA)", type="primary", use_container_width=True):
                with st.spinner("Sincronizando com o banco de dados..."):
                    try:
                        houve_mudanca = False
                        for index, row in df_editado.iterrows():
                            orig = df.loc[index]
                            if (str(orig['nome']) != str(row['nome']) or str(orig['grupo']) != str(row['grupo']) or int(orig['peso']) != int(row['peso']) or bool(orig['eh_fatal']) != bool(row['eh_fatal']) or bool(orig['esta_ativo']) != bool(row['esta_ativo']) or str(orig['departamento']) != str(row['departamento'])):
                                houve_mudanca = True
                                upd_payload = {
                                    "nome": str(row["nome"]), "grupo": str(row["grupo"]),
                                    "peso": int(row["peso"]), "eh_fatal": bool(row["eh_fatal"]),
                                    "esta_ativo": bool(row["esta_ativo"]), "departamento": str(row["departamento"])
                                }
                                supabase.table("criterios_qa").update(upd_payload).eq("id", row["id"]).execute()
                                
                                if bool(orig['esta_ativo']) != bool(row['esta_ativo']):
                                    acao = "Ativou" if row['esta_ativo'] else "Desativou"
                                    registrar_auditoria("STATUS CRITÉRIO QA", f"{acao} o critério: '{row['nome']}'", "Geral", usuario_logado)
                                else:
                                    registrar_auditoria("EDIÇÃO CRITÉRIO QA", f"Editou o critério: '{row['nome']}'", "Geral", usuario_logado)
                        
                        if houve_mudanca:
                            st.toast("✅ Base de critérios atualizada!", icon="💾")
                            time.sleep(1); st.rerun()
                        else: st.info("Nenhuma alteração detectada.")
                    except Exception as e: st.error(f"Erro na atualização: {e}")
        else: st.info("Nenhum critério cadastrado.")

    # ==========================================================
    # ABA 2: CRITÉRIOS COMPORTAMENTAIS (PDI)
    # ==========================================================
    with aba_pdi:
        with st.expander("➕ Adicionar Nova Soft Skill (PDI)", expanded=False):
            with st.form("novo_pdi_form", clear_on_submit=True):
                st.markdown("### Nova Competência Comportamental")
                c_nome_pdi, c_dept_pdi = st.columns([2, 1])
                nome_pdi = c_nome_pdi.text_input("Nome da Soft Skill", placeholder="Ex: Inteligência Emocional")
                dept_pdi = c_dept_pdi.selectbox("Departamento", OPCOES_DEPARTAMENTO, index=len(OPCOES_DEPARTAMENTO)-1)
                desc_pdi = st.text_input("Descrição Curta", placeholder="Como o gestor deve avaliar?")
                
                if st.form_submit_button("💾 Salvar Competência PDI", type="primary"):
                    if nome_pdi:
                        try:
                            payload_pdi = {
                                "nome": nome_pdi.strip(), "descricao": desc_pdi.strip(), 
                                "departamento": dept_pdi, "esta_ativo": True
                            }
                            supabase.table("criterios_comportamentais").insert(payload_pdi).execute()
                            registrar_auditoria("CRIAR CRITÉRIO PDI", f"Adicionou Skill: {nome_pdi}", "Geral", usuario_logado)
                            st.toast(f"✅ Skill adicionada!", icon="🎯")
                            time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                    else: st.warning("⚠️ Nome obrigatório.")

        st.divider()
        st.subheader("📝 Editar Competências do PDI")
        try:
            res_comp = supabase.table("criterios_comportamentais").select("*").order("nome").execute()
            df_comp = pd.DataFrame(res_comp.data) if res_comp.data else pd.DataFrame()
            
            if not df_comp.empty:
                if 'departamento' not in df_comp.columns: df_comp['departamento'] = 'Todos'

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
                    houve_mudanca = False
                    for index, r in df_edit_comp.iterrows():
                        orig_pdi = df_comp.loc[index]
                        if (str(orig_pdi['nome']) != str(r['nome']) or str(orig_pdi.get('descricao', '')) != str(r.get('descricao', '')) or str(orig_pdi.get('departamento', 'Todos')) != str(r.get('departamento', 'Todos')) or bool(orig_pdi['esta_ativo']) != bool(r['esta_ativo'])):
                            houve_mudanca = True
                            p_pdi = {
                                "nome": str(r["nome"]), "descricao": str(r.get("descricao", "")), 
                                "departamento": str(r.get("departamento", "Todos")), "esta_ativo": bool(r["esta_ativo"])
                            }
                            supabase.table("criterios_comportamentais").update(p_pdi).eq("id", r["id"]).execute()
                            
                            if bool(orig_pdi['esta_ativo']) != bool(r['esta_ativo']):
                                acao = "Ativou" if r['esta_ativo'] else "Desativou"
                                registrar_auditoria("STATUS CRITÉRIO PDI", f"{acao} a skill: '{r['nome']}'", "Geral", usuario_logado)
                            else: registrar_auditoria("EDIÇÃO CRITÉRIO PDI", f"Editou a skill: '{r['nome']}'", "Geral", usuario_logado)
                    
                    if houve_mudanca:
                        st.toast("✅ PDI Atualizado!")
                        time.sleep(1); st.rerun()
                    else: st.info("Nenhuma alteração detectada.")
        except Exception as e: st.info(f"Crie o primeiro critério de PDI acima. (Erro: {e})")

    # ==========================================================
    # ABA 3: CRITÉRIOS DE LIDERANÇA (360) - COMENTADO
    # ==========================================================
    # with aba_lid:
    #     with st.expander("➕ Adicionar Novo Critério de Liderança", expanded=False):
    #         with st.form("novo_lid_form", clear_on_submit=True):
    #             st.markdown("### Novo Critério para Avaliar Gestores")
    #             nome_lid = st.text_input("Nome do Critério", placeholder="Ex: Comunicação Clara")
    #             desc_lid = st.text_input("Descrição", placeholder="Como o SDR deve avaliar isso?")
    #             
    #             if st.form_submit_button("💾 Salvar Critério de Liderança", type="primary"):
    #                 if nome_lid:
    #                     try:
    #                         payload_lid = {
    #                             "nome": nome_lid.strip(), 
    #                             "descricao": desc_lid.strip(), 
    #                             "esta_ativo": True
    #                         }
    #                         supabase.table("criterios_lideranca").insert(payload_lid).execute()
    #                         registrar_auditoria("CRIAR CRITÉRIO LIDERANÇA", f"Adicionou critério: {nome_lid}", "Geral", usuario_logado)
    #                         st.toast(f"✅ Critério adicionado!", icon="🎯")
    #                         time.sleep(1); st.rerun()
    #                     except Exception as e: st.error(f"Erro: {e}")
    #                 else: st.warning("⚠️ O Nome do critério é obrigatório.")
    #
    #     st.divider()
    #     st.subheader("📝 Editar Critérios de Liderança")
    #     try:
    #         res_lid = supabase.table("criterios_lideranca").select("*").order("nome").execute()
    #         df_lid = pd.DataFrame(res_lid.data) if res_lid.data else pd.DataFrame()
    #         
    #         if not df_lid.empty:
    #             df_edit_lid = st.data_editor(
    #                 df_lid[['id', 'nome', 'descricao', 'esta_ativo']],
    #                 column_config={
    #                     "id": st.column_config.TextColumn("ID", disabled=True),
    #                     "nome": st.column_config.TextColumn("Nome do Critério", required=True),
    #                     "esta_ativo": st.column_config.CheckboxColumn("Ativo?")
    #                 },
    #                 hide_index=True, use_container_width=True
    #             )
    #
    #             if st.button("🔄 Salvar Alterações em Massa (Liderança)", type="primary", use_container_width=True):
    #                 houve_mudanca = False
    #                 for index, r in df_edit_lid.iterrows():
    #                     orig_lid = df_lid.loc[index]
    #                     
    #                     if (str(orig_lid['nome']) != str(r['nome']) or
    #                         str(orig_lid.get('descricao', '')) != str(r.get('descricao', '')) or
    #                         bool(orig_lid['esta_ativo']) != bool(r['esta_ativo'])):
    #                         
    #                         houve_mudanca = True
    #                         p_lid = {
    #                             "nome": str(r["nome"]), "descricao": str(r.get("descricao", "")), 
    #                             "esta_ativo": bool(r["esta_ativo"])
    #                         }
    #                         supabase.table("criterios_lideranca").update(p_lid).eq("id", r["id"]).execute()
    #                         
    #                         if bool(orig_lid['esta_ativo']) != bool(r['esta_ativo']):
    #                             acao = "Ativou" if r['esta_ativo'] else "Desativou"
    #                             registrar_auditoria("STATUS CRITÉRIO LIDERANÇA", f"{acao} o critério: '{r['nome']}'", "Geral", usuario_logado)
    #                         else:
    #                             registrar_auditoria("EDIÇÃO CRITÉRIO LIDERANÇA", f"Editou o critério: '{r['nome']}'", "Geral", usuario_logado)
    #                 
    #                 if houve_mudanca:
    #                     st.toast("✅ Critérios Atualizados com Sucesso!")
    #                     time.sleep(1); st.rerun()
    #                 else:
    #                     st.info("Nenhuma alteração detectada.")
    #     except Exception as e:
    #         st.info(f"Crie o primeiro critério de Liderança acima. (Erro: {e})")