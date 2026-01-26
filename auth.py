import streamlit as st
from database import supabase

def verificar_login(email, senha):
    res = supabase.table("usuarios").select("nome_exibicao, nivel").eq("login_email", email).eq("senha", senha).eq("esta_ativo", True).execute()
    if res.data:
        st.session_state.authenticated = True
        st.session_state.user = res.data[0]['nome_exibicao']
        st.session_state.nivel = res.data[0]['nivel']
        return True
    return False

def render_login():
    st.title("🔐 Login - Acelera Quality")
    with st.form("login_form"):
        user = st.text_input("E-mail")
        pwd = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if verificar_login(user, pwd):
                st.rerun()
            else:
                st.error("Credenciais inválidas.")