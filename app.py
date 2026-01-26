import streamlit as st
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_monitoria
from cadastro import render_cadastro
from database import get_all_records_db

def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        render_login()
        st.stop()

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        nivel = st.session_state.get('nivel', 'sdr').upper()
        options = ["DASHBOARD", "MONITORIA", "HISTÓRICO"]
        if nivel == "ADMIN": options.append("CADASTRO")
        
        page = st.radio("Navegação", options)
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()

    if page == "DASHBOARD": render_dashboard()
    elif page == "MONITORIA": render_monitoria()
    elif page == "CADASTRO": render_cadastro()
    elif page == "HISTÓRICO":
        st.title("📜 Histórico")
        st.dataframe(get_all_records_db(), use_container_width=True)

if __name__ == "__main__":
    main()