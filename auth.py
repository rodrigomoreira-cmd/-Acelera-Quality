import streamlit as st
from database import supabase

def verificar_login(username, senha):
    # Busca por 'user' e 'senha' conforme imagem do seu banco
    res = supabase.table("usuarios").select("nome, nivel") \
        .eq("user", username) \
        .eq("senha", senha) \
        .execute()
    
    if res.data:
        st.session_state.authenticated = True
        st.session_state.user = res.data[0]['nome']
        st.session_state.nivel = res.data[0]['nivel'].lower()
        return True
    return False

def render_login():
    st.title("🔐 Login - Acelera Quality")
    with st.form("login_form"):
        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if verificar_login(user, pwd):
                st.rerun()
            else:
                st.error("Credenciais inválidas.")