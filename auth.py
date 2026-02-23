import streamlit as st
import time
import hashlib
from database import supabase, registrar_auditoria
from datetime import datetime, timedelta

def hash_password(password):
    """Gera o hash SHA-256 para comparação segura."""
    return hashlib.sha256(str.encode(password.strip())).hexdigest()

def render_login(cookie_manager):
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔐 Acelera Quality")
        
        # ==========================================================
        # 🛡️ FASE 2: BOTÃO COFRE (Garante a gravação do Cookie Novo)
        # ==========================================================
        if 'usuario_aprovado' in st.session_state:
            u = st.session_state.usuario_aprovado
            
            expiry = datetime.now() + timedelta(days=1)
            cookie_manager.set('user_token', u['user'], expires_at=expiry)
            
            st.success(f"✅ Identidade confirmada, {u['nome']}!")
            st.info("Credenciais de segurança atualizadas. Clique abaixo para prosseguir.")
            
            if st.button("🚀 Entrar no Painel", type="primary", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.force_logout = False
                st.session_state.user_nome = u['nome']
                st.session_state.user_login = u['user']
                st.session_state.nivel = str(u.get('nivel', 'USUARIO')).upper()
                
                dept_banco = u.get('departamento')
                st.session_state.departamento = dept_banco if dept_banco and str(dept_banco).strip() != "" else "Sem Departamento"
                st.session_state.foto_url = u.get('foto_url')
                
                registrar_auditoria("LOGIN", "Acesso manual efetuado.", "N/A", u['nome'])
                
                del st.session_state['usuario_aprovado']
                st.rerun()
                
            return 
            
        # ==========================================================
        # 📝 FASE 1: FORMULÁRIO DE LOGIN NORMAL
        # ==========================================================
        st.markdown("Faça login para acessar o sistema.")
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("E-mail", placeholder="seu.email@grupoacelerador.com.br")
            password = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Verificar Credenciais", use_container_width=True, type="primary"):
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
                                st.session_state.usuario_aprovado = user_data
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")

        st.markdown("<div style='text-align: center; color: gray; font-size: 12px; margin-top: 20px;'>Acelera Quality v2.0 • Sistema Seguro</div>", unsafe_allow_html=True)