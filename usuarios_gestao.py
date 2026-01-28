import streamlit as st
import re
from database import supabase

def render_usuario_gestao():
    st.title("👤 Gerenciamento de Perfil")
    
    user_logado = st.session_state.user
    nivel = st.session_state.get('nivel', 'sdr').upper()
    
    # Busca dados (com tratamento de erro caso a secret falhe)
    try:
        res = supabase.table("usuarios").select("*").eq("nome", user_logado).execute()
        if not res.data:
            st.error("Usuário não encontrado no banco.")
            return
        dados_user = res.data[0]
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return

    email_atual = dados_user.get('email', '')
    prefixo_atual = email_atual.split('@')[0] if '@' in email_atual else email_atual

    st.subheader("Meus Dados")
    
    # Organização Vertical: Um campo abaixo do outro
    st.text_input("Nome Completo", value=dados_user['nome'], disabled=True)
    st.text_input("Usuário de Login", value=dados_user['user'], disabled=True)
    
    # E-mail em bloco único
    st.write("**E-mail Institucional**")
    c_p, c_d = st.columns([2, 1])
    with c_p:
        st.text_input("Prefixo", value=prefixo_atual, disabled=(nivel != "ADMIN"), label_visibility="collapsed", key="meu_prefixo")
    with c_d:
        st.info("@grupoacelerador.com.br")
            
    st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=(nivel != "ADMIN"))

    with st.expander("🔐 Alterar Minha Senha"):
        n_senha = st.text_input("Nova Senha", type="password", key="new_pass")
        c_senha = st.text_input("Confirme a Senha", type="password", key="conf_pass")
        if st.button("Atualizar Senha", use_container_width=True):
            if n_senha == c_senha and n_senha != "":
                supabase.table("usuarios").update({"senha": n_senha}).eq("id", dados_user['id']).execute()
                st.success("✅ Senha alterada!")
            else:
                st.error("❌ Verifique as senhas.")