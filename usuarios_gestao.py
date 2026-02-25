import streamlit as st
import pandas as pd
from database import get_all_records_db, supabase, registrar_auditoria
import time

def render_usuario_gestao():
    st.title("👥 Gestão de Equipe e Acessos")
    st.markdown("Gerencie os colaboradores, níveis de acesso, status e redefina senhas perdidas.")

    nivel_logado = st.session_state.get('nivel', 'USUARIO').upper()
    dept_logado = st.session_state.get('departamento', 'Todos')
    nome_logado = st.session_state.get('user_nome', 'Desconhecido')

    # Proteção de acesso: Apenas liderança pode entrar
    if nivel_logado not in ["ADMIN", "GESTAO", "GERENCIA"]:
        st.error("🚫 Acesso restrito. Apenas administradores e gestores podem visualizar esta página.")
        return

    df_users = get_all_records_db("usuarios")
    if df_users is None or df_users.empty:
        st.warning("Nenhum usuário encontrado na base de dados.")
        return

    # ==========================================================
    # 🛡️ TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
    # ==========================================================
    if nivel_logado != "ADMIN":
        # Remove a conta mestre da lista para qualquer um que não seja ADMIN
        if 'email' in df_users.columns:
            df_users = df_users[df_users['email'] != 'admin@grupoacelerador.com.br'].copy()
        elif 'nome' in df_users.columns:
            df_users = df_users[df_users['nome'] != 'admin@grupoacelerador.com.br'].copy() # Caso não tenha email na view, corta pelo nome se for igual

    # ==========================================================
    # FILTRO DE VISIBILIDADE (Quem o gestor pode editar?)
    # ==========================================================
    if nivel_logado in ["ADMIN", "GERENCIA"]:
        df_filtrado = df_users.copy() # Admin e Gerência veem todos (já sem o admin mestre se for gerência)
    else:
        # Gestão comum vê apenas o seu departamento
        df_filtrado = df_users[df_users['departamento'].str.upper() == dept_logado.upper()].copy()

    # Organiza a lista colocando os ativos primeiro e em ordem alfabética
    if 'ativo' not in df_filtrado.columns:
        df_filtrado['ativo'] = True
    
    df_filtrado = df_filtrado.sort_values(by=['ativo', 'nome'], ascending=[False, True])

    # ==========================================================
    # PAINEL DE INDICADORES
    # ==========================================================
    qtd_total = len(df_filtrado)
    qtd_ativos = len(df_filtrado[df_filtrado['ativo'] == True])
    qtd_inativos = qtd_total - qtd_ativos

    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Total de Colaboradores", qtd_total)
    c2.metric("✅ Contas Ativas", qtd_ativos)
    c3.metric("🚫 Contas Inativas", qtd_inativos)

    st.divider()

    # ==========================================================
    # SELEÇÃO DE USUÁRIO PARA EDIÇÃO
    # ==========================================================
    st.subheader("⚙️ Editar Colaborador")
    
    # Criar uma lista visual com o status (ex: "🟢 João Silva", "🔴 Maria Souza (Inativa)")
    opcoes_formatadas = []
    mapa_usuarios = {}
    
    for _, row in df_filtrado.iterrows():
        status_icone = "🟢" if row.get('ativo', True) else "🔴"
        status_texto = "" if row.get('ativo', True) else " (Inativo)"
        label = f"{status_icone} {row['nome']}{status_texto}"
        opcoes_formatadas.append(label)
        mapa_usuarios[label] = row['id'] # Guarda o ID real para podermos buscar os dados

    escolha = st.selectbox("Busque e selecione o colaborador:", [""] + opcoes_formatadas)

    if escolha:
        user_id = mapa_usuarios[escolha]
        user_data = df_filtrado[df_filtrado['id'] == user_id].iloc[0]
        
        c_form, c_acoes = st.columns([2, 1], gap="large")
        
        # ==========================================================
        # FORMULÁRIO DE EDIÇÃO CADASTRAL
        # ==========================================================
        with c_form:
            with st.container(border=True):
                st.markdown("#### 📝 Dados de Cadastro")
                with st.form(f"form_edit_{user_id}"):
                    novo_nome = st.text_input("Nome Completo", value=user_data['nome'])
                    novo_email = st.text_input("E-mail / Login", value=user_data.get('email', ''))
                    
                    col_d, col_n = st.columns(2)
                    
                    # Tratamento de Departamento
                    opcoes_dept = ["SDR", "Especialista", "Venda de Ingresso", "Auditor", "Gestão", "Gerência", "Outros"]
                    dept_atual = user_data.get('departamento', 'SDR')
                    if dept_atual not in opcoes_dept: opcoes_dept.append(dept_atual)
                    novo_dept = col_d.selectbox("Departamento", opcoes_dept, index=opcoes_dept.index(dept_atual))
                    
                    # Tratamento de Nível de Acesso
                    opcoes_nivel = ["USUARIO", "AUDITOR", "GESTAO", "GERENCIA", "ADMIN"]
                    nivel_atual = user_data.get('nivel', 'USUARIO').upper()
                    if nivel_atual not in opcoes_nivel: opcoes_nivel.append(nivel_atual)
                    
                    # Proteção: Apenas um ADMIN pode dar privilégios de ADMIN para alguém
                    pode_editar_nivel = nivel_logado == "ADMIN"
                    novo_nivel = col_n.selectbox(
                        "Nível de Acesso do Sistema", 
                        opcoes_nivel, 
                        index=opcoes_nivel.index(nivel_atual),
                        disabled=not pode_editar_nivel,
                        help="Apenas o Administrador Geral pode alterar o Nível de Acesso." if not pode_editar_nivel else ""
                    )

                    st.divider()
                    # Toggle de Ativar/Desativar
                    status_atual = user_data.get('ativo', True)
                    novo_status = st.toggle("Conta Ativa", value=bool(status_atual), help="Desligue para bloquear o login deste usuário sem apagar seu histórico.")

                    if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                        payload = {
                            "nome": novo_nome,
                            "email": novo_email,
                            "departamento": novo_dept,
                            "nivel": novo_nivel,
                            "ativo": novo_status
                        }
                        try:
                            supabase.table("usuarios").update(payload).eq("id", user_id).execute()
                            registrar_auditoria("EDICAO_USUARIO", f"Atualizou cadastro de {novo_nome}. Status: {'Ativo' if novo_status else 'Inativo'}", novo_nome, nome_logado)
                            st.success(f"✅ Cadastro de {novo_nome} atualizado com sucesso!")
                            get_all_records_db.clear()
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco de dados: {e}")

        # ==========================================================
        # PAINEL DE AÇÕES CRÍTICAS (SENHA E EXCLUSÃO)
        # ==========================================================
        with c_acoes:
            with st.container(border=True):
                st.markdown("#### 🔐 Segurança")
                st.caption("Ações críticas da conta.")
                
                # REDEFINIR SENHA
                @st.dialog("🔑 Redefinir Senha")
                def modal_senha():
                    st.warning(f"Redefinir a senha de **{user_data['nome']}**?")
                    st.markdown("Crie uma nova senha temporária. O colaborador deverá utilizá-la no próximo login.")
                    nova_senha = st.text_input("Nova Senha:", value="Mudar123", type="password")
                    
                    if st.button("Confirmar Troca", type="primary", use_container_width=True):
                        if len(nova_senha) < 6:
                            st.error("A senha deve ter no mínimo 6 caracteres.")
                        else:
                            try:
                                supabase.table("usuarios").update({"senha": nova_senha}).eq("id", user_id).execute()
                                registrar_auditoria("REDEFINICAO_SENHA", "A senha foi resetada pela liderança.", user_data['nome'], nome_logado)
                                st.success("✅ Senha alterada! Avise o colaborador.")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

                if st.button("🔑 Gerar Nova Senha", use_container_width=True):
                    modal_senha()
                
                st.divider()
                st.caption("💡 **Dica:** Para desligamentos, recomendamos apenas desmarcar o botão 'Conta Ativa' no formulário ao lado para preservar o histórico do colaborador.")