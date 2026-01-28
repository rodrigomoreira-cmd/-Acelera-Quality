import streamlit as st
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_monitoria
from cadastro import render_cadastro
from contestacao import render_contestacao
from usuarios_gestao import render_usuario_gestao 
from database import get_all_records_db
from style import apply_custom_styles  

def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    if not st.session_state.authenticated:
        render_login()
        st.stop()

    apply_custom_styles()
    nivel = st.session_state.get('nivel', 'sdr').upper()

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.get('user', 'Usuário')}")
        st.write(f"Nível: {nivel}")
        st.divider()

        def menu_button(label, icon, page_name):
            if st.button(f"{icon} {label}", use_container_width=True, 
                         type="primary" if st.session_state.current_page == page_name else "secondary"):
                st.session_state.current_page = page_name
                st.rerun()

        # Chamadas com 3 argumentos para evitar erro
        menu_button("DASHBOARD", "📊", "DASHBOARD")
        menu_button("MEU PERFIL", "👤", "PERFIL")
        menu_button("CONTESTAR NOTA", "⚖️", "CONTESTACAO")
        menu_button("HISTÓRICO", "📜", "HISTORICO")

        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("**Gestão**")
            # Procure a linha 46 e garanta que ela tenha o ícone entre aspas:
            menu_button("DASHBOARD", "📊", "DASHBOARD")
            menu_button("NOVA MONITORIA", "📝", "MONITORIA")
            menu_button("CADASTRO SDR", "👥", "CADASTRO")

        st.divider()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    page = st.session_state.current_page
    if page == "DASHBOARD": render_dashboard()
    elif page == "PERFIL": render_usuario_gestao()
    elif page == "CONTESTACAO": render_contestacao() 
    elif page == "HISTORICO":
        st.title("📜 Histórico")
        df = get_all_records_db("monitorias")
        if df is not None and not df.empty:
            if nivel == "SDR": df = df[df['sdr'] == st.session_state.user]
            st.dataframe(df, use_container_width=True, hide_index=True)
    elif page == "MONITORIA" and nivel == "ADMIN": render_monitoria()
    elif page == "CADASTRO" and nivel == "ADMIN": render_cadastro()

if __name__ == "__main__":
    main()