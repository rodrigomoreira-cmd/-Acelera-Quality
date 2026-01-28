import streamlit as st
import re
from database import supabase

def validar_prefixo(prefixo):
    padrao = r'^[a-zA-Z0-9._]+$'
    return re.match(padrao, prefixo) is not None

def formatar_telefone(tel):
    numeros = re.sub(r'\D', '', tel)
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return tel

def render_usuario_gestao():
    st.title("👤 Gerenciamento de Perfil")
    
    user_logado = st.session_state.user
    nivel = st.session_state.get('nivel', 'sdr').upper()
    
    # Busca dados do banco
    res = supabase.table("usuarios").select("*").eq("nome", user_logado).execute()
    
    if not res.data:
        st.error("Erro ao carregar dados do perfil.")
        return

    dados_user = res.data[0]
    email_atual = dados_user.get('email', '')
    prefixo_atual = email_atual.split('@')[0] if '@' in email_atual else email_atual

    st.subheader("Meus Dados")
    
    # CAMPOS UM ABAIXO DO OUTRO
    st.text_input("Nome Completo", value=dados_user['nome'], disabled=True)
    st.text_input("Usuário de Login", value=dados_user['user'], disabled=True)
    
    st.write("**E-mail Institucional**")
    col_pref, col_dom = st.columns([2, 1])
    p_disabled = False if nivel == "ADMIN" else True
    
    with col_pref:
        novo_pref = st.text_input("Prefixo", value=prefixo_atual, disabled=p_disabled, label_visibility="collapsed")
    with col_dom:
        st.info("@grupoacelerador.com.br")
            
    st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=p_disabled)

    with st.expander("🔐 Alterar Minha Senha"):
        n_senha = st.text_input("Nova Senha", type="password")
        c_senha = st.text_input("Confirme a Senha", type="password")
        if st.button("Atualizar Senha", use_container_width=True):
            if n_senha == c_senha and n_senha != "":
                supabase.table("usuarios").update({"senha": n_senha}).eq("id", dados_user['id']).execute()
                st.success("Senha alterada!")
            else:
                st.error("Senhas não coincidem.")