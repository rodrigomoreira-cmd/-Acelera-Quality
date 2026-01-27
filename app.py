import streamlit as st
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_monitoria
from cadastro import render_cadastro
from contestacao import render_contestacao
from database import get_all_records_db

def main():
    st.markdown(f"""
    <style>
    /* Fundo principal e da barra lateral */
    .stApp, [data-testid="stSidebar"] {{
        background-color: {THEME['bg']};
        color: {THEME['text']};
    }}
    
    /* Botões Primários (Laranja) */
    div.stButton > button:first-child {{
        background-color: {THEME['accent']};
        color: white;
        border: None;
    }}
    
    /* Tabelas e Dataframes */
    [data-testid="stDataFrame"] {{
        background-color: {THEME['card']};
    }}
    </style>
    """, unsafe_allow_html=True)

    st.set_page_config(layout="wide", page_title="Acelera Quality")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    if not st.session_state.authenticated:
        render_login()
        st.stop()

    nivel = st.session_state.get('nivel', 'sdr').upper()

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.write(f"Nível: {nivel}")
        st.divider()

        def menu_button(label, icon, page_name):
            if st.button(f"{icon} {label}", use_container_width=True, 
                         type="primary" if st.session_state.current_page == page_name else "secondary"):
                st.session_state.current_page = page_name
                st.rerun()

        # MENU PARA SDR
        menu_button("DASHBOARD", "📊", "DASHBOARD")
        menu_button("CONTESTAR NOTA", "⚖️", "CONTESTACAO")
        menu_button("HISTÓRICO", "📜", "HISTORICO")

        # MENU ADICIONAL PARA ADMIN
        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("**Gestão**")
            menu_button("NOVA MONITORIA", "📝", "MONITORIA")
            menu_button("CADASTRO SDR", "👥", "CADASTRO")

        st.divider()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # ROTEAMENTO
    page = st.session_state.current_page

    if page == "DASHBOARD":
        render_dashboard()
    
    elif page == "CONTESTACAO":
        render_contestacao() # Função trata visualização de SDR vs ADMIN
    
    elif page == "HISTORICO":
        st.title("📜 Histórico de Monitorias")
        df = get_all_records_db()
        if not df.empty:
            if nivel == "SDR":
                # SDR só vê as dele (Leitura)
                df = df[df['sdr'] == st.session_state.user]
                st.info("Seu histórico de performance")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro encontrado.")

    # PROTEÇÃO DE ROTAS ADMIN
    elif page == "MONITORIA" and nivel == "ADMIN":
        render_monitoria()
    elif page == "CADASTRO" and nivel == "ADMIN":
        render_cadastro()

if __name__ == "__main__":
    main()