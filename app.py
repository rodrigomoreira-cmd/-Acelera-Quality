import streamlit as st
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_monitoria
from cadastro import render_cadastro
from contestacao import render_contestacao # Novo import
from database import get_all_records_db

def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    # Gerenciamento de Estado
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # Sidebar com Botões
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        nivel = st.session_state.get('nivel', 'sdr').upper()
        st.write(f"Nível: {nivel}")
        st.divider()

        # Função auxiliar para criar botões de menu
        def menu_button(label, icon, page_name):
            if st.button(f"{icon} {label}", use_container_width=True, 
                         type="primary" if st.session_state.current_page == page_name else "secondary"):
                st.session_state.current_page = page_name
                st.rerun()

        menu_button("DASHBOARD", "📊", "DASHBOARD")
        menu_button("MONITORIA", "📝", "MONITORIA")
        menu_button("CONTESTAÇÃO", "⚖️", "CONTESTACAO")

        # Histórico e Cadastro visíveis apenas para ADMIN
        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("**Gestão**")
            menu_button("HISTÓRICO", "📜", "HISTORICO")
            menu_button("CADASTRO", "👥", "CADASTRO")

        st.divider()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # Roteamento de Páginas
    page = st.session_state.current_page
    if page == "DASHBOARD":
        render_dashboard()
    elif page == "MONITORIA":
        render_monitoria()
    elif page == "CONTESTACAO":
        render_contestacao()
    elif page == "CADASTRO":
        render_cadastro()
    elif page == "HISTORICO":
        # Bloqueio de segurança redundante
        if nivel == "ADMIN":
            st.title("📜 Histórico Geral de Monitorias")
            df = get_all_records_db()
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Acesso restrito ao Administrador.")

if __name__ == "__main__":
    main()