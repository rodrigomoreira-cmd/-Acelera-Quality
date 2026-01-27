import streamlit as st
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_monitoria
from cadastro import render_cadastro
from database import get_all_records_db

def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    # 1. GERENCIAMENTO DE ESTADO
    # Inicializa a autenticação
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # Inicializa a página padrão se não houver uma selecionada
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    # 2. BLOQUEIO DE LOGIN
    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # 3. SIDEBAR COM BOTÕES
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        nivel = st.session_state.get('nivel', 'sdr').upper()
        st.write(f"Nível: {nivel}")
        st.divider()

        st.markdown("### Navegação")

        # Botão Dashboard
        if st.button("📊 DASHBOARD", use_container_width=True, 
                     type="primary" if st.session_state.current_page == "DASHBOARD" else "secondary"):
            st.session_state.current_page = "DASHBOARD"
            st.rerun()

        # Botão Monitoria
        if st.button("📝 MONITORIA", use_container_width=True,
                     type="primary" if st.session_state.current_page == "MONITORIA" else "secondary"):
            st.session_state.current_page = "MONITORIA"
            st.rerun()

        # Botão Histórico
        if st.button("📜 HISTÓRICO", use_container_width=True,
                     type="primary" if st.session_state.current_page == "HISTÓRICO" else "secondary"):
            st.session_state.current_page = "HISTÓRICO"
            st.rerun()

        # Botão Cadastro (Restrito a ADMIN)
        if nivel == "ADMIN":
            if st.button("👥 CADASTRO", use_container_width=True,
                         type="primary" if st.session_state.current_page == "CADASTRO" else "secondary"):
                st.session_state.current_page = "CADASTRO"
                st.rerun()

        st.divider()
        
        # Botão Sair
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.authenticated = False
            # Opcional: limpa a página atual ao sair
            st.session_state.current_page = "DASHBOARD"
            st.rerun()

    # 4. ROTEAMENTO DE PÁGINAS
    page = st.session_state.current_page

    if page == "DASHBOARD":
        render_dashboard()
    elif page == "MONITORIA":
        render_monitoria()
    elif page == "CADASTRO":
        render_cadastro()
    elif page == "HISTÓRICO":
        st.title("📜 Histórico")
        # Busca os registros do banco modularizado
        df = get_all_records_db()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro encontrado.")

if __name__ == "__main__":
    main()