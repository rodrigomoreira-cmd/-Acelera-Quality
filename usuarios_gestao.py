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
    res = supabase.table("usuarios").select("*").eq("nome", user_logado).execute()
    
    if not res.data:
        st.error("Erro ao carregar dados do perfil.")
        return

    dados_user = res.data[0]
    email_atual = dados_user.get('email', '')
    prefixo_atual = email_atual.split('@')[0] if '@' in email_atual else email_atual

    st.subheader("Meus Dados")
    
    # Grid principal para alinhamento
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.text_input("Nome", value=dados_user['nome'], disabled=True)
        st.text_input("Usuário de Acesso", value=dados_user['user'], disabled=True)

    with col_dir:
        # Rótulo manual para alinhar com o campo "Nome"
        st.markdown("<label style='font-size: 14px;'>E-mail Institucional</label>", unsafe_allow_html=True)
        
        # Sub-colunas com proporção ajustada para caber na tela
        c_pref, c_dom = st.columns([1.3, 1])
        p_disabled = False if nivel == "ADMIN" else True
        
        with c_pref:
            novo_pref = st.text_input("Prefixo", value=prefixo_atual, disabled=p_disabled, label_visibility="collapsed")
        with c_dom:
            st.info("@grupoacelerador.com.br")
            
        st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=p_disabled)

    st.divider()

    # Seção de Senha
    with st.expander("🔐 Alterar Minha Senha"):
        n_senha = st.text_input("Nova Senha", type="password")
        c_senha = st.text_input("Confirme a Senha", type="password")
        if st.button("Atualizar Senha", use_container_width=True):
            if n_senha == c_senha and n_senha != "":
                supabase.table("usuarios").update({"senha": n_senha}).eq("id", dados_user['id']).execute()
                st.success("✅ Senha alterada!")
            else:
                st.error("❌ Senhas não coincidem.")

    # Painel Administrativo
    if nivel == "ADMIN":
        st.subheader("🛠️ Gestão de Usuários (ADMIN)")
        # ... (lógica de gestão de usuários mantida) ...