import hashlib
import os

import streamlit as st

from database import registrar_auditoria, supabase


def hash_password(password):
    """Gera o hash SHA-256 para comparação segura."""
    return hashlib.sha256(str.encode(password.strip())).hexdigest()


def render_login():
    # ==========================================
    # 🎨 ESTILIZAÇÃO PREMIUM DA TELA DE LOGIN
    # ==========================================
    st.markdown(
        """
    <style>
    /* Estilo da caixa do formulário (Efeito de sombra e borda na cor do sistema) */
    div[data-testid="stForm"] {
        border: 2px solid #ff4b4b33;
        border-radius: 15px;
        padding: 30px;
        box-shadow: 0 10px 30px -10px rgba(255, 75, 75, 0.2);
        background: linear-gradient(145deg, #1e1e1e, #262626);
    }
    /* Deixa o botão de Entrar com a cor exata da marca e efeito Hover */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #ff3333;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
        transform: translateY(-2px);
    }
    /* Ajusta a barra superior preta do Streamlit para não atrapalhar */
    header {visibility: hidden;}
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Criação das colunas para centralizar o formulário
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)

        # ==========================================
        # 🏢 LOGO DA EMPRESA
        # ==========================================
        c_logo1, c_logo2, c_logo3 = st.columns([1, 2, 1])
        with c_logo2:
            if os.path.exists("assets/logo.png"):
                st.image("assets/logo.png", use_container_width=True)
            else:
                st.markdown(
                    "<h1 style='text-align: center; color: #ff4b4b; margin-bottom: 0;'>ACELERA</h1><h3 style='text-align: center; color: white; margin-top: 0;'>QUALITY</h3>",
                    unsafe_allow_html=True,
                )

        st.markdown(
            "<p style='text-align: center; color: #aaaaaa; margin-bottom: 20px;'>Faça login para acessar o painel de performance.</p>",
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "E-mail", placeholder="seu.email@grupoacelerador.com.br"
            )
            password = st.text_input("Senha", type="password", placeholder="••••••••")

            st.markdown(
                "<br>", unsafe_allow_html=True
            )  # Espacinho extra antes do botão

            if st.form_submit_button(
                "Entrar no Sistema", use_container_width=True, type="primary"
            ):
                if not email or not password:
                    st.warning("Preencha todos os campos.")
                else:
                    email_limpo = email.lower().strip()
                    password_limpo = password.strip()

                    try:
                        # CORREÇÃO APLICADA AQUI: Busca feita pela coluna 'email'
                        response = (
                            supabase.table("usuarios")
                            .select("*")
                            .ilike("email", email_limpo)
                            .execute()
                        )
                        user_data = response.data[0] if response.data else None

                        if not user_data:
                            st.error("Usuário não encontrado.")
                        elif not user_data.get("esta_ativo", True):
                            st.error("🚫 Acesso bloqueado. Contate o administrador.")
                        else:
                            senha_banco = user_data.get("senha")
                            if (
                                hash_password(password_limpo) == senha_banco
                                or password_limpo == senha_banco
                            ):
                                # LOGIN DIRETO NA SESSÃO (SEM COOKIES)
                                st.session_state.authenticated = True
                                st.session_state.user_nome = user_data["nome"]
                                # Prevenção extra: se 'user' estiver vazio no banco, usa o e-mail como fallback
                                st.session_state.user_login = user_data.get(
                                    "user", email_limpo
                                )
                                st.session_state.nivel = str(
                                    user_data.get("nivel", "USUARIO")
                                ).upper()

                                dept_banco = user_data.get("departamento")
                                st.session_state.departamento = (
                                    dept_banco
                                    if dept_banco and str(dept_banco).strip() != ""
                                    else "Sem Departamento"
                                )
                                st.session_state.foto_url = user_data.get("foto_url")

                                registrar_auditoria(
                                    "LOGIN",
                                    "Acesso efetuado com sucesso.",
                                    "N/A",
                                    user_data["nome"],
                                )

                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")

        st.markdown(
            "<div style='text-align: center; color: #666; font-size: 12px; margin-top: 30px;'>Acelera Quality v2.0 • Ambiente Seguro e Criptografado</div>",
            unsafe_allow_html=True,
        )
