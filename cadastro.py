import streamlit as st
from database import supabase

def render_cadastro():
    st.title("👥 Cadastro de Usuários")
    
    with st.form("form_novo_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome Completo")
        user_login = col2.text_input("Login (Usuário)")
        
        senha = col1.text_input("Senha", type="password")
        # Campo de seleção de nível
        nivel = col2.selectbox("Nível de Acesso", ["sdr", "admin"])
        
        email = st.text_input("E-mail")

        if st.form_submit_button("Finalizar Cadastro"):
            if nome and user_login and senha:
                try:
                    payload = {
                        "nome": nome,
                        "user": user_login, # Certifique-se que o nome da coluna no banco é 'user'
                        "senha": senha,
                        "nivel": nivel,
                        "email": email
                    }
                    supabase.table("usuarios").insert(payload).execute()
                    st.success(f"Usuário {user_login} criado como {nivel.upper()}!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")