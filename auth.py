import streamlit as st
from database import supabase
from recuperacao import render_recuperacao

def render_login():
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    if st.session_state.auth_mode == "recuperar":
        if st.button("⬅️ Voltar para Login", key="back_to_login"):
            st.session_state.auth_mode = "login"
            st.rerun()
        render_recuperacao()
        return

    st.title("🚀 Acelera Quality")
    
    with st.container():
        user_input = st.text_input("Usuário", key="login_user")
        password = st.text_input("Senha", type="password", key="login_pass")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Entrar", use_container_width=True, type="primary"):
                if user_input and password:
                    login_busca = user_input.strip().lower()
                    res = supabase.table("usuarios").select("*").eq("user", login_busca).eq("senha", password).execute()
                    
                    if res.data:
                        dados = res.data[0]
                        st.session_state.authenticated = True
                        st.session_state.user_login = dados['user'] 
                        st.session_state.user_nome = dados.get('nome', 'Usuário sem Nome')
                        st.session_state.nivel = str(dados.get('nivel', 'SDR')).upper()
                        st.session_state.current_page = "DASHBOARD"
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos.")
                else:
                    st.warning("⚠️ Preencha todos os campos.")

        with col_btn2:
            if st.button("Esqueci minha senha", use_container_width=True):
                st.session_state.auth_mode = "recuperar"
                st.rerun()