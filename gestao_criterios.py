import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria, get_all_records_db
import time

def render_gestao_criterios():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados.")
        return
    # ------------------------------------------------------------------

    # 🎨 PALETA DE CORES SISTÊMICA
    COR_PRINCIPAL = "#FF7A00"  # Laranja vibrante principal
    COR_TEXTO = "#A0AEC0"

    st.markdown(
        f"<h1 style='color: {COR_PRINCIPAL};'>⚙️ Configuração de Critérios</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Gerencie os modelos de checklist de monitoria e competências do PDI de forma centralizada."
    )

    usuario_logado = str(st.session_state.get("user_nome", "Sistema"))
    
    # 👇 PUXA O FILTRO DA BARRA LATERAL
    dept_logado = str(st.session_state.get("departamento_selecionado", "Todos"))

    OPCOES_DEPARTAMENTO = [
        "SDR",
        "Especialista",
        "Venda de Ingresso",
        "Auditor",
        "Gestão",
        "Gerência",
        "Todos",
    ]
    
    # Define o índice padrão baseado no filtro global da sidebar
    indice_dept_padrao = OPCOES_DEPARTAMENTO.index(dept_logado) if dept_logado in OPCOES_DEPARTAMENTO else len(OPCOES_DEPARTAMENTO) - 1

    # ==========================================================
    # SISTEMA DE ABAS
    # ==========================================================
    aba_qa, aba_pdi = st.tabs(["📑 Modelos de Checklist (QA)", "🎯 Competências PDI"])

    # ==========================================================
    # ABA 1: CONSTRUTOR DE CHECKLISTS VERSIONADOS
    # ==========================================================
    with aba_qa:
        st.write("##")
        with st.expander("➕ Criar Novo Modelo de Checklist", expanded=False):
            with st.container(border=True):
                st.markdown(f"<h4 style='color: {COR_PRINCIPAL}; margin-top: 0;'>📝 Construtor de Formulário</h4>", unsafe_allow_html=True)
                st.markdown("Preencha os dados do modelo e adicione as perguntas na tabela abaixo.")
                
                c_nome, c_versao, c_perfil = st.columns([2, 1, 1])
                nome_modelo = c_nome.text_input("Nome do Checklist", placeholder="Ex: Avaliação Outbound")
                versao_modelo = c_versao.text_input("Versão", placeholder="Ex: v1.0")
                # Já vem pré-preenchido com o filtro global:
                perfil_modelo = c_perfil.selectbox("Perfil Alvo", OPCOES_DEPARTAMENTO, index=indice_dept_padrao)

                st.markdown("#### 📋 Perguntas do Checklist")
                st.caption("Adicione ou edite as linhas abaixo. Linhas com a pergunta vazia serão ignoradas automaticamente.")
                
                # Tabela inicial vazia para o gestor preencher
                df_perguntas_base = pd.DataFrame([
                    {"Grupo": "N1", "Pergunta": "", "Peso": 1, "Fatal": False},
                    {"Grupo": "N1", "Pergunta": "", "Peso": 1, "Fatal": False},
                    {"Grupo": "N2", "Pergunta": "", "Peso": 3, "Fatal": False},
                    {"Grupo": "N3", "Pergunta": "", "Peso": 7, "Fatal": False},
                    {"Grupo": "N3", "Pergunta": "", "Peso": 7, "Fatal": False},
                ])

                df_editado = st.data_editor(
                    df_perguntas_base,
                    column_config={
                        "Grupo": st.column_config.SelectboxColumn("Nível (Aba)", options=["N1", "N2", "N3"], required=True),
                        "Pergunta": st.column_config.TextColumn("Critério / Pergunta", width="large"),
                        "Peso": st.column_config.SelectboxColumn("Penalidade (%)", options=[1, 3, 7], required=True),
                        "Fatal": st.column_config.CheckboxColumn("Zera Nota? (Fatal)"),
                    },
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True
                )

                st.write("")
                if st.button("💾 Salvar Modelo de Checklist", type="primary", use_container_width=True):
                    df_valido = df_editado[df_editado["Pergunta"].str.strip() != ""]
                    
                    if not nome_modelo or not versao_modelo:
                        st.error("⚠️ O Nome do Modelo e a Versão são obrigatórios!")
                    elif df_valido.empty:
                        st.error("⚠️ Adicione pelo menos uma pergunta válida ao checklist!")
                    else:
                        with st.spinner("Salvando novo modelo..."):
                            perguntas_json = df_valido.to_dict(orient="records")
                            payload = {
                                "nome": nome_modelo.strip(),
                                "versao": versao_modelo.strip(),
                                "perfil": perfil_modelo,
                                "ativo": True,
                                "perguntas": perguntas_json
                            }
                            try:
                                supabase.table("modelos_checklist").insert(payload).execute() # type: ignore
                                registrar_auditoria(
                                    "CRIAR MODELO CHECKLIST", 
                                    f"Criou checklist '{nome_modelo}' versão '{versao_modelo}' para {perfil_modelo}", 
                                    "Geral", 
                                    usuario_logado
                                )
                                st.success(f"✅ Modelo {nome_modelo} ({versao_modelo}) salvo com sucesso!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar modelo: {e}")

        st.divider()
        st.markdown(f"### 📚 Biblioteca de Checklists ({dept_logado})")
        st.caption("Ative, desative ou exclua os formulários que ficarão disponíveis para os auditores.")
        
        try:
            # APLICAÇÃO DO FILTRO GLOBAL NA BUSCA DOS MODELOS
            query_modelos = supabase.table("modelos_checklist").select("*").order("criado_em", desc=True)
            if dept_logado != "Todos":
                query_modelos = query_modelos.eq("perfil", dept_logado)
                
            res_modelos = query_modelos.execute() # type: ignore
            
            if res_modelos.data:
                for mod in res_modelos.data:
                    status_txt = "🟢 ATIVO" if mod['ativo'] else "🔴 INATIVO"
                    with st.expander(f"{status_txt} | {mod['nome']} (Versão: {mod['versao']}) - Perfil: {mod['perfil']}"):
                        
                        df_display = pd.DataFrame(mod['perguntas'])
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                        
                        st.write("")
                        
                        # Colunas para alinhar o toggle de ativar/desativar e o botão de excluir
                        col_toggle, col_delete = st.columns([3, 1])
                        
                        with col_toggle:
                            ativo_toggle = st.toggle("Habilitar para uso nas Monitorias", value=mod['ativo'], key=f"tgl_{mod['id']}")
                            if ativo_toggle != mod['ativo']:
                                supabase.table("modelos_checklist").update({"ativo": ativo_toggle}).eq("id", mod['id']).execute() # type: ignore
                                acao = "Ativou" if ativo_toggle else "Desativou"
                                registrar_auditoria("STATUS MODELO CHECKLIST", f"{acao} o checklist: '{mod['nome']} {mod['versao']}'", "Geral", usuario_logado)
                                st.rerun()
                                
                        with col_delete:
                            # 👇 BOTÃO DE EXCLUIR
                            if st.button("🗑️ Excluir Modelo", key=f"del_{mod['id']}", use_container_width=True):
                                try:
                                    supabase.table("modelos_checklist").delete().eq("id", mod['id']).execute() # type: ignore
                                    registrar_auditoria("EXCLUIR MODELO CHECKLIST", f"Apagou o checklist: '{mod['nome']} {mod['versao']}'", "Geral", usuario_logado)
                                    st.success("✅ Modelo excluído!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir modelo: {e}")
            else:
                st.info(f"Nenhum modelo de checklist encontrado para o filtro atual: {dept_logado}.")
        except Exception as e:
            st.error(f"Erro ao buscar os modelos: {e}")

    # ==========================================================
    # ABA 2: CRITÉRIOS COMPORTAMENTAIS (PDI)
    # ==========================================================
    with aba_pdi:
        st.write("##")
        with st.expander("➕ Adicionar Nova Soft Skill (PDI)", expanded=False):
            with st.container(border=True):
                with st.form("novo_pdi_form", clear_on_submit=True, border=False):
                    st.markdown(
                        f"<h4 style='color: {COR_PRINCIPAL}; margin-top: 0;'>🎯 Nova Competência Comportamental</h4>",
                        unsafe_allow_html=True,
                    )

                    c_nome_pdi, c_dept_pdi = st.columns([2, 1])
                    nome_pdi = c_nome_pdi.text_input(
                        "Nome da Soft Skill",
                        placeholder="Ex: Inteligência Emocional, Resiliência...",
                    )
                    # Já vem pré-preenchido com o filtro global:
                    dept_pdi = c_dept_pdi.selectbox("Departamento", OPCOES_DEPARTAMENTO, index=indice_dept_padrao)

                    desc_pdi = st.text_area(
                        "Descrição Curta",
                        placeholder="Como o gestor deve avaliar esta competência na equipe?",
                        height=100,
                    )

                    st.write("")
                    if st.form_submit_button("💾 Salvar Competência", type="primary", use_container_width=True):
                        if nome_pdi:
                            try:
                                payload_pdi = {
                                    "nome": str(nome_pdi).strip(),
                                    "descricao": str(desc_pdi).strip(),
                                    "departamento": str(dept_pdi),
                                    "esta_ativo": True,
                                }
                                supabase.table("criterios_comportamentais").insert(payload_pdi).execute()  # type: ignore
                                registrar_auditoria("CRIAR CRITÉRIO PDI", f"Adicionou Skill: {nome_pdi}", "Geral", usuario_logado)
                                st.toast(f"✅ Soft Skill adicionada!", icon="🎯")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        else:
                            st.warning("⚠️ O nome da competência é obrigatório.")

        st.divider()
        st.markdown(f"### 📝 Gerenciar Matriz de PDI ({dept_logado})")
        st.caption("Edite os nomes, descrições ou desative habilidades da matriz de desenvolvimento.")

        try:
            query_pdi = supabase.table("criterios_comportamentais").select("*").order("nome")
            if dept_logado != "Todos":
                query_pdi = query_pdi.eq("departamento", dept_logado)
                
            res_comp = query_pdi.execute()  # type: ignore
            df_comp = pd.DataFrame(res_comp.data) if hasattr(res_comp, "data") and res_comp.data else pd.DataFrame()

            if not df_comp.empty:
                if "departamento" not in df_comp.columns:
                    df_comp["departamento"] = "Todos"

                df_comp["esta_ativo"] = df_comp["esta_ativo"].astype(bool)

                df_edit_comp = st.data_editor(
                    df_comp[["id", "nome", "descricao", "departamento", "esta_ativo"]],
                    column_config={
                        "id": st.column_config.TextColumn("ID", disabled=True),
                        "nome": st.column_config.TextColumn("Nome da Skill", width="medium", required=True),
                        "descricao": st.column_config.TextColumn("Guia de Avaliação", width="large"),
                        "departamento": st.column_config.SelectboxColumn("Dept", options=OPCOES_DEPARTAMENTO),
                        "esta_ativo": st.column_config.CheckboxColumn("Ativo?"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=400,
                )

                st.write("")
                if st.button("🔄 Salvar Alterações em Massa (PDI)", type="primary", use_container_width=True):
                    with st.spinner("Atualizando matriz de PDI..."):
                        houve_mudanca = False
                        for index, r in df_edit_comp.iterrows():
                            if pd.isna(r.get("id")):
                                continue

                            orig_pdi = df_comp.loc[int(str(index))]  # type: ignore
                            
                            if (
                                str(orig_pdi["nome"]) != str(r["nome"])
                                or str(orig_pdi.get("descricao", "")) != str(r.get("descricao", ""))
                                or str(orig_pdi.get("departamento", "Todos")) != str(r.get("departamento", "Todos"))
                                or bool(orig_pdi["esta_ativo"]) != bool(r["esta_ativo"])
                            ):
                                houve_mudanca = True
                                p_pdi = {
                                    "nome": str(r["nome"]),
                                    "descricao": str(r.get("descricao", "")),
                                    "departamento": str(r.get("departamento", "Todos")),
                                    "esta_ativo": bool(r["esta_ativo"]),
                                }
                                supabase.table("criterios_comportamentais").update(p_pdi).eq("id", r["id"]).execute()  # type: ignore

                                if bool(orig_pdi["esta_ativo"]) != bool(r["esta_ativo"]):
                                    acao = "Ativou" if r["esta_ativo"] else "Desativou"
                                    registrar_auditoria("STATUS CRITÉRIO PDI", f"{acao} a skill: '{r['nome']}'", "Geral", usuario_logado)
                                else:
                                    registrar_auditoria("EDIÇÃO CRITÉRIO PDI", f"Editou a skill: '{r['nome']}'", "Geral", usuario_logado)

                        if houve_mudanca:
                            st.success("✅ Matriz de Desenvolvimento (PDI) atualizada com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("Nenhuma alteração detectada na tabela.")
            else:
                st.info(f"Nenhum critério comportamental encontrado para o filtro atual: {dept_logado}.")
        except Exception as e:
            st.error(f"Erro ao carregar matriz de PDI: {e}")