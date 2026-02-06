import streamlit as st
import time
import hashlib
from database import supabase, registrar_auditoria
from datetime import datetime, timedelta

def hash_password(password):
    """Gera o hash SHA-256 para comparação segura."""
    return hashlib.sha256(str.encode(password.strip())).hexdigest()

def render_login(cookie_manager):
    # Layout centralizado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔐 Acelera Quality")
        st.markdown("Faça login para acessar o sistema.")
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("E-mail", placeholder="seu.email@grupoacelerador.com.br")
            password = st.text_input("Senha", type="password")
            
            submit = st.form_submit_button("Entrar", use_container_width=True, type="primary")
            
            if submit:
                if not email or not password:
                    st.warning("Preencha todos os campos.")
                else:
                    # Limpeza preventiva (minúsculo e sem espaços)
                    email_limpo = email.lower().strip()
                    password_limpo = password.strip()
                    
                    try:
                        # 1. Busca o usuário no banco (usando ilike para ignorar maiúsculas/minúsculas)
                        response = supabase.table("usuarios").select("*").ilike("user", email_limpo).execute()
                        user_data = response.data[0] if response.data else None
                        
                        if not user_data:
                            st.error("Usuário não encontrado.")
                        elif not user_data.get('esta_ativo', True):
                            st.error("🚫 Acesso bloqueado. Contate o administrador.")
                        else:
                            # --- LÓGICA DE VERIFICAÇÃO DE SENHA (HÍBRIDA) ---
                            senha_banco = user_data.get('senha')  # ou 'password', conforme seu banco
                            
                            # Calcula o hash da senha que foi digitada agora
                            hash_digitado = hash_password(password_limpo)
                            
                            acesso_permitido = False
                            
                            # Verificação 1: A senha digitada bate com o Hash do banco? (Usuários com senha nova)
                            if hash_digitado == senha_banco:
                                acesso_permitido = True
                                
                            # Verificação 2: A senha digitada é IGUAL ao texto do banco? (Usuários antigos/Legado)
                            elif password_limpo == senha_banco:
                                acesso_permitido = True
                                # Opcional: Avisar para trocar a senha futuramente
                            
                            if acesso_permitido:
                                # SUCESSO! Configura a sessão
                                st.success(f"Bem-vindo, {user_data['nome']}!")
                                
                                # Define variáveis de sessão
                                st.session_state.authenticated = True
                                st.session_state.user_nome = user_data['nome']
                                st.session_state.user_login = user_data['user'] # Salva o email exato do banco
                                st.session_state.nivel = str(user_data.get('nivel', 'SDR')).upper()
                                st.session_state.foto_url = user_data.get('foto_url')
                                
                                # Grava Cookie de 24h
                                expiry = datetime.now() + timedelta(days=1)
                                cookie_manager.set('user_token', user_data['user'], expires_at=expiry)
                                
                                # Auditoria de Login
                                registrar_auditoria("LOGIN", user_data['nome'], "Acesso realizado via Auth.")
                                
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                                
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")

        st.markdown("""
            <div style='text-align: center; color: gray; font-size: 12px; margin-top: 20px;'>
                Acelera Quality v2.0 • Sistema Seguro
            </div>
        """, unsafe_allow_html=True)