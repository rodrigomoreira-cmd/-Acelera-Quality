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
    # Criamos 3 colunas: as das pontas vazias para "espremer" o centro
    # A proporção [1, 1, 1] ou [1, 2, 1] controla a largura do formulário
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True) # Espaçamento superior
        st.title("🔐 Login")
        st.subheader("Acelera Quality")
        
        with st.form("login_form"):
            user = st.text_input("Usuário")
            pwd = st.text_input("Senha", type="password")
            
            # Botão de submissão
            submit = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit:
                if verificar_login(user, pwd):
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")