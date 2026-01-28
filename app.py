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
    # 1. Configuração Inicial
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    # 2. Gerenciamento de Estado
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    # 3. Bloqueio de Login
    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # 4. Aplicação de Estilo
    apply_custom_styles()

    nivel = st.session_state.get('nivel', 'sdr').upper()

    # 5. Sidebar com Navegação
    with st.sidebar:
        nome_usuario = st.session_state.get('user', 'Usuário')
        st.markdown(f"### 👤 {nome_usuario}")
        st.write(f"Nível: {nivel}")
        st.divider()

        def menu_button(label, icon, page_name):
            # Corrige o erro de TypeError garantindo 3 argumentos
            if st.button(f"{icon} {label}", use_container_width=True, 
                         type="primary" if st.session_state.current_page == page_name else "secondary"):
                st.session_state.current_page = page_name
                st.rerun()

        # Chamadas Corrigidas com 3 argumentos: (Texto, Ícone, Página)
        menu_button("DASHBOARD", "📊", "DASHBOARD")
        menu_button("MEU PERFIL", "👤", "PERFIL")
        menu_button("CONTESTAR NOTA", "⚖️", "CONTESTACAO")
        menu_button("HISTÓRICO", "📜", "HISTORICO")

        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("**Gestão de Equipe**")
            menu_button("NOVA MONITORIA", "📝", "MONITORIA")
            menu_button("CADASTRO SDR", "👥", "CADASTRO")

        st.divider()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # 6. Roteamento de Páginas
    page = st.session_state.current_page

    if page == "DASHBOARD":
        render_dashboard()
    elif page == "PERFIL":
        render_usuario_gestao()
    elif page == "CONTESTACAO":
        render_contestacao() 
    elif page == "HISTORICO":
        st.title("📜 Histórico de Monitorias")
        df = get_all_records_db("monitorias") 
        if df is not None and not df.empty:
            if nivel == "SDR":
                df = df[df['sdr'] == st.session_state.user]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro encontrado.")
    elif page == "MONITORIA" and nivel == "ADMIN":
        render_monitoria()
    elif page == "CADASTRO" and nivel == "ADMIN":
        render_cadastro()

if __name__ == "__main__":
    main()