import streamlit as st
import re
from database import supabase

def render_cadastro():
    st.title("👥 Cadastro de Novo Colaborador")

    with st.container():
        nome = st.text_input("Nome Completo")
        usuario = st.text_input("Usuário de Acesso")
        
        st.write("**E-mail Institucional**")
        col_p, col_d = st.columns([2, 1])
        with col_p:
            prefixo = st.text_input("Prefixo", label_visibility="collapsed")
        with col_d:
            st.info("@grupoacelerador.com.br")
            
        telefone = st.text_input("Telefone (DDD + Número)")
        nivel = st.selectbox("Nível de Acesso", ["SDR", "ADMIN"])
        senha = st.text_input("Senha Inicial", type="password")

    if st.button("🚀 Finalizar Cadastro", use_container_width=True):
        if not nome or not usuario or not prefixo or not senha:
            st.error("Preencha todos os campos obrigatórios.")
        else:
            email_f = f"{prefixo.strip().lower()}@grupoacelerador.com.br"
            payload = {
                "nome": nome, "user": usuario, "email": email_f, 
                "telefone": telefone, "nivel": nivel.lower(), "senha": senha
            }
            supabase.table("usuarios").insert(payload).execute()
            st.success(f"Usuário {nome} cadastrado!")