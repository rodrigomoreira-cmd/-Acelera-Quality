import streamlit as st
from database import supabase

def render_usuario_gestao():
    st.title("👤 Gerenciamento de Perfil")
    
    user_logado = st.session_state.user
    nivel = st.session_state.nivel.upper()

    # 1. BUSCA DADOS DO USUÁRIO NO BANCO
    res = supabase.table("usuarios").select("*").eq("nome", user_logado).execute()
    
    if not res.data:
        st.error("Erro ao carregar dados do perfil.")
        return

    dados_user = res.data[0]

    # --- VISÃO DO SDR (OU DADOS PRÓPRIOS DO ADMIN) ---
    st.subheader("Meus Dados")
    col1, col2 = st.columns(2)

    with col1:
        st.text_input("Nome", value=dados_user['nome'], disabled=True)
        st.text_input("Usuário de Acesso", value=dados_user['user'], disabled=True)
        
    with col2:
        # Admin pode editar seu próprio email, SDR apenas visualiza
        email_disabled = False if nivel == "ADMIN" else True
        novo_email = st.text_input("Email", value=dados_user.get('email', ''), disabled=email_disabled)
        
        # Campo de telefone (exemplo conforme sua solicitação)
        novo_tel = st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=email_disabled)

    # BOTÃO ALTERAR SENHA (Disponível para todos)
    with st.expander("🔐 Alterar Minha Senha"):
        nova_senha = st.text_input("Nova Senha", type="password")
        confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
        
        if st.button("Atualizar Senha"):
            if nova_senha == confirma_senha and nova_senha != "":
                supabase.table("usuarios").update({"senha": nova_senha}).eq("id", dados_user['id']).execute()
                st.success("Senha alterada com sucesso!")
            else:
                st.error("As senhas não coincidem ou estão vazias.")

    st.divider()

    # --- VISÃO EXCLUSIVA DO ADMIN (GESTÃO TOTAL) ---
    if nivel == "ADMIN":
        st.subheader("🛠️ Painel de Controle de Usuários (ADMIN)")
        
        # Busca todos os usuários para o Admin gerenciar
        todos_users = supabase.table("usuarios").select("*").execute()
        df_users = todos_users.data

        if df_users:
            st.write("Selecione um colaborador para editar:")
            nomes_sdrs = [u['nome'] for u in df_users]
            sdr_para_editar = st.selectbox("Colaborador", nomes_sdrs)

            # Filtra dados do selecionado
            target = next(item for item in df_users if item["nome"] == sdr_para_editar)

            with st.container():
                edit_email = st.text_input("Editar Email do Colaborador", value=target.get('email', ''))
                edit_tel = st.text_input("Editar Telefone do Colaborador", value=target.get('telefone', ''))
                edit_senha = st.text_input("Resetar Senha do Colaborador", placeholder="Digite nova senha se desejar alterar")

                if st.button(f"Salvar Alterações em {sdr_para_editar}"):
                    updates = {
                        "email": edit_email,
                        "telefone": edit_tel
                    }
                    if edit_senha:
                        updates["senha"] = edit_senha
                    
                    supabase.table("usuarios").update(updates).eq("id", target['id']).execute()
                    st.success(f"Dados de {sdr_para_editar} atualizados com sucesso!")
                    st.rerun()

        st.divider()
        st.subheader("📜 Histórico Geral de Cadastros")
        st.dataframe(df_users, use_container_width=True)