import streamlit as st
import hashlib
from database import supabase, registrar_auditoria

def hash_password(password):
    """Gera o hash SHA-256 para comparação segura."""
    return hashlib.sha256(str.encode(password.strip())).hexdigest()

def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔐 Acelera Quality")
        st.markdown("Faça login para acessar o sistema.")
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("E-mail", placeholder="seu.email@grupoacelerador.com.br")
            password = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Entrar", use_container_width=True, type="primary"):
                if not email or not password:
                    st.warning("Preencha todos os campos.")
                else:
                    email_limpo = email.lower().strip()
                    password_limpo = password.strip()
                    
                    try:
                        response = supabase.table("usuarios").select("*").ilike("user", email_limpo).execute()
                        user_data = response.data[0] if response.data else None
                        
                        if not user_data:
                            st.error("Usuário não encontrado.")
                        elif not user_data.get('esta_ativo', True):
                            st.error("🚫 Acesso bloqueado. Contate o administrador.")
                        else:
                            senha_banco = user_data.get('senha')
                            if hash_password(password_limpo) == senha_banco or password_limpo == senha_banco:
                                
                                # LOGIN DIRETO NA SESSÃO (SEM COOKIES)
                                st.session_state.authenticated = True
                                st.session_state.user_nome = user_data['nome']
                                st.session_state.user_login = user_data['user']
                                st.session_state.nivel = str(user_data.get('nivel', 'USUARIO')).upper()
                                
                                dept_banco = user_data.get('departamento')
                                st.session_state.departamento = dept_banco if dept_banco and str(dept_banco).strip() != "" else "Sem Departamento"
                                st.session_state.foto_url = user_data.get('foto_url')
                                
                                registrar_auditoria("LOGIN", "Acesso efetuado com sucesso.", "N/A", user_data['nome'])
                                
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")

        st.markdown("<div style='text-align: center; color: gray; font-size: 12px; margin-top: 20px;'>Acelera Quality v2.0 • Sistema Seguro</div>", unsafe_allow_html=True)