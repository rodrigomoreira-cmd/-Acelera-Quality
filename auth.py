import streamlit as st
import time
from datetime import datetime, timedelta
from database import supabase
from recuperacao import render_recuperacao 

def render_login(cookie_manager=None):
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    # Lógica de Recuperação de Senha
    if st.session_state.auth_mode == "recuperar":
        if st.button("⬅️ Voltar para Login"):
            st.session_state.auth_mode = "login"
            st.rerun()
        render_recuperacao()
        return

    # Estilo Dark Mode para a tela de Login
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stHeader"] {display: none;}
            .stApp { background-color: #000000 !important; }
            h1, h2, h3, p, label { color: #ffffff !important; }
            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #111111 !important;
                border: 1px solid #333333 !important;
                border-radius: 15px !important;
                padding: 30px !important;
            }
            input { background-color: #222222 !important; color: #ffffff !important; border: 1px solid #444444 !important; }
        </style>
    """, unsafe_allow_html=True)

    _, col_central, _ = st.columns([1, 1.8, 1])

    with col_central:
        st.write("##")
        st.markdown("<h1 style='text-align: center;'>🚀 Acelera Quality</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("Login")
            user_input = st.text_input("Usuário (E-mail)", key="login_user").strip().lower()
            password = st.text_input("Senha", type="password", key="login_pass")
            
            st.write("#")
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Entrar", use_container_width=True, type="primary"):
                    if user_input and password:
                        try:
                            # Busca o usuário no Supabase
                            res = supabase.table("usuarios").select("*").eq("user", user_input).eq("senha", password).execute()
                            
                            if res.data:
                                dados = res.data[0]
                                if not dados.get('esta_ativo', True):
                                    st.error("Conta desativada. Fale com o Admin.")
                                    return

                                # --- SUCESSO NO LOGIN ---
                                
                                # 1. Define Variáveis de Sessão IMEDIATAMENTE
                                st.session_state.authenticated = True
                                st.session_state.user_login = dados['user'] 
                                st.session_state.user_nome = dados.get('nome', user_input)
                                st.session_state.nivel = str(dados.get('nivel', 'SDR')).upper()
                                st.session_state.foto_url = dados.get('foto_url')
                                st.session_state.current_page = "DASHBOARD"
                                
                                # LIMPEZA CRÍTICA: Garante que o sistema pare de ignorar o login automático
                                st.session_state.logout_clicked = False
                                
                                # 2. Grava o Cookie (user_token) com validade de 10 minutos
                                if cookie_manager:
                                    expires = datetime.now() + timedelta(minutes=10)
                                    # Usamos a mesma chave 'user_token' que o app.py procura
                                    cookie_manager.set('user_token', dados['user'], expires_at=expires, key="login_session")
                                
                                st.success("Acesso autorizado! Carregando...")
                                
                                # Pequena pausa para garantir que o navegador salvou o cookie antes do rerun
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("❌ Usuário ou senha incorretos.")
                        except Exception as e:
                            st.error(f"Erro de conexão: {e}")
                    else:
                        st.warning("⚠️ Preencha todos os campos.")

            with col_btn2:
                if st.button("Recuperar Senha", use_container_width=True):
                    st.session_state.auth_mode = "recuperar"
                    st.rerun()

        st.markdown("<p style='text-align: center; color: #555; margin-top:20px;'>Acelera Quality v2.7 | Sessão Segura 10min</p>", unsafe_allow_html=True)