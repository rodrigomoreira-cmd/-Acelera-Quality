import streamlit as st
import pandas as pd
from database import supabase

def render_cadastro():
    st.title("👥 Cadastro de Usuários")
    
    with st.form("form_novo_user", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome Completo")
        login = col2.text_input("Login/Usuário")
        senha = col1.text_input("Senha", type="password")
        
        # Seleção de Nível solicitada
        nivel = col2.selectbox("Nível de Acesso", ["sdr", "admin"])
        email = st.text_input("E-mail")

        if st.form_submit_button("Cadastrar"):
            if nome and login and senha:
                try:
                    payload = {
                        "nome": nome,
                        "user": login,
                        "senha": senha,
                        "nivel": nivel,
                        "email": email
                    }
                    supabase.table("usuarios").insert(payload).execute()
                    st.success(f"Usuário {login} criado como {nivel.upper()}!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")