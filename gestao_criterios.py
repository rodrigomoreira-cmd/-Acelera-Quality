import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria
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
        "Gerencie as perguntas do checklist de monitoria e competências do PDI de forma centralizada."
    )

    usuario_logado = str(st.session_state.get("user_nome", "Sistema"))

    OPCOES_CATEGORIAS = [
        "Nectar CRM",
        "Ambos - Processo SDR",
        "Identificar - Processo",
        "Integração",
        "Selene/Bot",
    ]
    OPCOES_DEPARTAMENTO = [
        "SDR",
        "Especialista",
        "Venda de Ingresso",
        "Auditor",
        "Todos",
    ]

    # ==========================================================
    # MODIFICADO: A TERCEIRA ABA (LIDERANÇA) FOI COMENTADA
    # ==========================================================
    aba_qa, aba_pdi = st.tabs(["🎧 Critérios de Qualidade (QA)", "🎯 Competências PDI"])

    # ==========================================================
    # ABA 1: CRITÉRIOS DE QUALIDADE (QA)
    # ==========================================================
    with aba_qa:
        st.write("##")
        with st.expander("➕ Adicionar Novo Critério QA", expanded=False):
            with st.container(border=True):
                with st.form("novo_item_qa_form", clear_on_submit=True, border=False):
                    st.markdown(
                        f"<h4 style='color: {COR_PRINCIPAL}; margin-top: 0;'>📝 Novo Item de Avaliação</h4>",
                        unsafe_allow_html=True,
                    )

                    nome = st.text_input(
                        "Pergunta / Critério",
                        placeholder="Ex: Confirmou os dados de contato no início da ligação?",
                    )

                    c_grupo, c_dept = st.columns(2)
                    grupo = c_grupo.selectbox(
                        "Categoria do Checklist", OPCOES_CATEGORIAS
                    )
                    departamento = c_dept.selectbox(
                        "Departamento Alvo", OPCOES_DEPARTAMENTO
                    )

                    st.write("")
                    st.markdown("#### ⚖️ Inteligência do Critério")
                    st.caption(
                        "Defina o peso desta pergunta para a média final e se o erro zera a nota da ligação."
                    )

                    col_p, col_f = st.columns([1.5, 1])
                    peso = col_p.select_slider(
                        "Peso do Item (Pontos)",
                        options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                        value=1,
                    )

                    col_f.write("")  # Espaçamento para alinhar com o slider
                    col_f.write("")
                    eh_fatal = col_f.toggle("🚨 Marcar como ITEM FATAL")

                    desc_ajuda = st.text_area(
                        "Guia para o Auditor (Opcional)",
                        placeholder="Dicas de como o avaliador deve julgar esta etapa...",
                        height=100,
                    )

                    st.write("")
                    if st.form_submit_button(
                        "💾 Salvar Novo Critério",
                        use_container_width=True,
                        type="primary",
                    ):
                        if nome:
                            try:
                                payload = {
                                    "nome": str(nome).strip(),
                                    "descricao": str(desc_ajuda).strip(),
                                    "grupo": grupo,
                                    "departamento": departamento,
                                    "peso": int(peso),
                                    "eh_fatal": bool(eh_fatal),
                                    "esta_ativo": True,
                                }
                                supabase.table("criterios_qa").insert(payload).execute()  # type: ignore
                                registrar_auditoria(
                                    "CRIAR CRITÉRIO QA",
                                    f"Criou critério '{nome}'",
                                    "Geral",
                                    usuario_logado,
                                )
                                st.toast(
                                    f"✅ Critério adicionado com sucesso!", icon="✨"
                                )
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")
                        else:
                            st.warning(
                                "⚠️ O campo 'Pergunta / Critério' é obrigatório."
                            )

        st.divider()
        st.markdown("### 📋 Tabela de Critérios Ativos")
        st.caption(
            "Edite pesos, nomes ou desative critérios diretamente na tabela abaixo. Clique no botão ao final para salvar."
        )

        try:
            res = supabase.table("criterios_qa").select("*").order("grupo", desc=False).execute()  # type: ignore
            df = (
                pd.DataFrame(res.data)
                if hasattr(res, "data") and res.data
                else pd.DataFrame()
            )
        except Exception as e:
            st.error(f"Erro ao buscar: {e}")
            df = pd.DataFrame()

        if not df.empty:
            # Garante tipos corretos para não dar warning no editor
            df["peso"] = (
                pd.to_numeric(df["peso"], errors="coerce").fillna(1).astype(int)
            )
            df["eh_fatal"] = df["eh_fatal"].astype(bool)
            df["esta_ativo"] = df["esta_ativo"].astype(bool)

            df_editado = st.data_editor(
                df[
                    [
                        "id",
                        "grupo",
                        "nome",
                        "peso",
                        "eh_fatal",
                        "esta_ativo",
                        "departamento",
                    ]
                ],
                column_config={
                    "id": st.column_config.TextColumn("ID", disabled=True),
                    "grupo": st.column_config.SelectboxColumn(
                        "Categoria", options=OPCOES_CATEGORIAS, required=True
                    ),
                    "nome": st.column_config.TextColumn(
                        "Critério / Pergunta", width="large", required=True
                    ),
                    "peso": st.column_config.NumberColumn(
                        "Peso", min_value=1, max_value=10, step=1
                    ),
                    "eh_fatal": st.column_config.CheckboxColumn("🚨 Fatal?"),
                    "esta_ativo": st.column_config.CheckboxColumn("Ativo?"),
                    "departamento": st.column_config.SelectboxColumn(
                        "Dept", options=OPCOES_DEPARTAMENTO
                    ),
                },
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic",
                height=400,
            )

            st.write("")
            if st.button(
                "🔄 Aplicar Alterações em Massa (QA)",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner("Sincronizando tabela com o banco de dados..."):
                    try:
                        houve_mudanca = False
                        for index, row in df_editado.iterrows():
                            # Se for uma linha nova inserida direto no editor (id is NaN)
                            if pd.isna(row.get("id")):
                                continue  # Ignoramos inserções direto na tabela por segurança, obrigando uso do form superior.

                            orig = df.loc[index]  # type: ignore

                            # Comparações seguras de tipo
                            if (
                                str(orig["nome"]) != str(row["nome"])
                                or str(orig["grupo"]) != str(row["grupo"])
                                or int(orig["peso"]) != int(row["peso"])
                                or bool(orig["eh_fatal"]) != bool(row["eh_fatal"])
                                or bool(orig["esta_ativo"]) != bool(row["esta_ativo"])
                                or str(orig["departamento"]) != str(row["departamento"])
                            ):

                                houve_mudanca = True
                                upd_payload = {
                                    "nome": str(row["nome"]),
                                    "grupo": str(row["grupo"]),
                                    "peso": int(row["peso"]),
                                    "eh_fatal": bool(row["eh_fatal"]),
                                    "esta_ativo": bool(row["esta_ativo"]),
                                    "departamento": str(row["departamento"]),
                                }
                                supabase.table("criterios_qa").update(upd_payload).eq("id", row["id"]).execute()  # type: ignore

                                if bool(orig["esta_ativo"]) != bool(row["esta_ativo"]):
                                    acao = (
                                        "Ativou" if row["esta_ativo"] else "Desativou"
                                    )
                                    registrar_auditoria(
                                        "STATUS CRITÉRIO QA",
                                        f"{acao} o critério: '{row['nome']}'",
                                        "Geral",
                                        usuario_logado,
                                    )
                                else:
                                    registrar_auditoria(
                                        "EDIÇÃO CRITÉRIO QA",
                                        f"Editou o critério: '{row['nome']}'",
                                        "Geral",
                                        usuario_logado,
                                    )

                        if houve_mudanca:
                            st.success(
                                "✅ Base de critérios de qualidade atualizada com sucesso!"
                            )
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("Nenhuma alteração detectada na tabela.")
                    except Exception as e:
                        st.error(f"Erro na atualização: {e}")
        else:
            st.info("Nenhum critério cadastrado no banco de dados ainda.")

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
                    dept_pdi = c_dept_pdi.selectbox(
                        "Departamento",
                        OPCOES_DEPARTAMENTO,
                        index=len(OPCOES_DEPARTAMENTO) - 1,
                    )

                    desc_pdi = st.text_area(
                        "Descrição Curta",
                        placeholder="Como o gestor deve avaliar esta competência na equipe?",
                        height=100,
                    )

                    st.write("")
                    if st.form_submit_button(
                        "💾 Salvar Competência",
                        type="primary",
                        use_container_width=True,
                    ):
                        if nome_pdi:
                            try:
                                payload_pdi = {
                                    "nome": str(nome_pdi).strip(),
                                    "descricao": str(desc_pdi).strip(),
                                    "departamento": str(dept_pdi),
                                    "esta_ativo": True,
                                }
                                supabase.table("criterios_comportamentais").insert(payload_pdi).execute()  # type: ignore
                                registrar_auditoria(
                                    "CRIAR CRITÉRIO PDI",
                                    f"Adicionou Skill: {nome_pdi}",
                                    "Geral",
                                    usuario_logado,
                                )
                                st.toast(f"✅ Soft Skill adicionada!", icon="🎯")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        else:
                            st.warning("⚠️ O nome da competência é obrigatório.")

        st.divider()
        st.markdown("### 📝 Gerenciar Matriz de PDI")
        st.caption(
            "Edite os nomes, descrições ou desative habilidades da matriz de desenvolvimento."
        )

        try:
            res_comp = supabase.table("criterios_comportamentais").select("*").order("nome").execute()  # type: ignore
            df_comp = (
                pd.DataFrame(res_comp.data)
                if hasattr(res_comp, "data") and res_comp.data
                else pd.DataFrame()
            )

            if not df_comp.empty:
                if "departamento" not in df_comp.columns:
                    df_comp["departamento"] = "Todos"

                df_comp["esta_ativo"] = df_comp["esta_ativo"].astype(bool)

                df_edit_comp = st.data_editor(
                    df_comp[["id", "nome", "descricao", "departamento", "esta_ativo"]],
                    column_config={
                        "id": st.column_config.TextColumn("ID", disabled=True),
                        "nome": st.column_config.TextColumn(
                            "Nome da Skill", width="medium", required=True
                        ),
                        "descricao": st.column_config.TextColumn(
                            "Guia de Avaliação", width="large"
                        ),
                        "departamento": st.column_config.SelectboxColumn(
                            "Dept", options=OPCOES_DEPARTAMENTO
                        ),
                        "esta_ativo": st.column_config.CheckboxColumn("Ativo?"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=400,
                )

                st.write("")
                if st.button(
                    "🔄 Salvar Alterações em Massa (PDI)",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner("Atualizando matriz de PDI..."):
                        houve_mudanca = False
                        for index, r in df_edit_comp.iterrows():
                            if pd.isna(r.get("id")):
                                continue

                            orig_pdi = df_comp.loc[index]  # type: ignore
                            if (
                                str(orig_pdi["nome"]) != str(r["nome"])
                                or str(orig_pdi.get("descricao", ""))
                                != str(r.get("descricao", ""))
                                or str(orig_pdi.get("departamento", "Todos"))
                                != str(r.get("departamento", "Todos"))
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

                                if bool(orig_pdi["esta_ativo"]) != bool(
                                    r["esta_ativo"]
                                ):
                                    acao = "Ativou" if r["esta_ativo"] else "Desativou"
                                    registrar_auditoria(
                                        "STATUS CRITÉRIO PDI",
                                        f"{acao} a skill: '{r['nome']}'",
                                        "Geral",
                                        usuario_logado,
                                    )
                                else:
                                    registrar_auditoria(
                                        "EDIÇÃO CRITÉRIO PDI",
                                        f"Editou a skill: '{r['nome']}'",
                                        "Geral",
                                        usuario_logado,
                                    )

                        if houve_mudanca:
                            st.success(
                                "✅ Matriz de Desenvolvimento (PDI) atualizada com sucesso!"
                            )
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.info("Nenhuma alteração detectada na tabela.")
        except Exception as e:
            st.info(f"Crie o primeiro critério de PDI acima. (Log: {e})")
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
