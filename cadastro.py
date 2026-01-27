import streamlit as st
import pandas as pd
from database import supabase

def render_cadastro():
    st.title("👥 Gestão de Usuários")
    
    # --- FORMULÁRIO DE CADASTRO ---
    with st.form("form_cadastro", clear_on_submit=True):
        st.subheader("Cadastrar Novo Usuário")
        col1, col2 = st.columns(2)
        
        nome = col1.text_input("Nome Completo")
        user_login = col2.text_input("Login (Usuário)")
        
        senha = col1.text_input("Senha", type="password")
        # Seleção de nível conforme solicitado anteriormente
        nivel = col2.selectbox("Nível de Acesso", ["sdr", "admin"])
        
        email = st.text_input("E-mail")

        if st.form_submit_button("Cadastrar Novo Usuário"):
            if nome and user_login and senha:
                try:
                    payload = {
                        "nome": nome,
                        "user": user_login,
                        "senha": senha,
                        "nivel": nivel,
                        "email": email
                    }
                    supabase.table("usuarios").insert(payload).execute()
                    st.success(f"Usuário {user_login} cadastrado com sucesso!")
                    st.rerun() # Atualiza a página para mostrar o novo usuário na lista
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha Nome, Login e Senha.")

    st.divider()

    # --- HISTÓRICO DE USUÁRIOS CADASTRADOS ---
    st.subheader("📜 Histórico de Usuários")
    
    try:
        # Busca todos os usuários da tabela
        res = supabase.table("usuarios").select("nome, user, nivel, email").execute()
        
        if res.data:
            df_users = pd.DataFrame(res.data)
            
            # Renomeia as colunas para exibição amigável
            df_users.columns = ["Nome Completo", "Login/Usuário", "Nível de Acesso", "E-mail"]
            
            # Exibe a tabela formatada
            st.dataframe(
                df_users, 
                use_container_width=True, 
                hide_index=True
            )
            
            st.caption(f"Total de usuários cadastrados: {len(df_users)}")
        else:
            st.info("Nenhum usuário encontrado no banco de dados.")
            
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")