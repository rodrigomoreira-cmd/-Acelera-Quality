import streamlit as st
import re
from database import supabase

def render_usuario_gestao():
    st.title("👤 Gerenciamento de Perfil")
    
    # Simulação de dados (substitua pela sua busca no banco)
    user_logado = st.session_state.get('user', 'Usuário')
    dados_user = {"nome": "Administrador Geral", "user": "admin.acelera", "email": "admin@grupoacelerador.com.br"}
    prefixo_atual = dados_user['email'].split('@')[0]

    st.subheader("Meus Dados")
    
    # Campos organizados um abaixo do outro para alinhamento perfeito
    st.text_input("Nome", value=dados_user['nome'], disabled=True)
    st.text_input("Usuário de Acesso", value=dados_user['user'], disabled=True)
    
    # Bloco do E-mail
    st.write("**E-mail Institucional**")
    col_p, col_d = st.columns([2, 1])
    with col_p:
        st.text_input("Prefixo", value=prefixo_atual, label_visibility="collapsed")
    with col_d:
        st.info("@grupoacelerador.com.br")
        
    st.text_input("Telefone", placeholder="(XX) XXXXX-XXXX")
    
    if st.button("🚀 Salvar Alterações", use_container_width=True):
        st.success("Dados atualizados!")