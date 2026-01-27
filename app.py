import streamlit as st
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_monitoria
from cadastro import render_cadastro
from contestacao import render_contestacao
from database import get_all_records_db

def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    # 1. Gerenciamento de Estado
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    # Bloqueio de Login
    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # Identificação do Nível de Acesso
    nivel = st.session_state.get('nivel', 'sdr').upper()

    # 2. Sidebar com Botões de Navegação
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.write(f"Nível: {nivel}")
        st.divider()

        # Função auxiliar para criar botões de menu
        def menu_button(label, icon, page_name):
            if st.button(f"{icon} {label}", use_container_width=True, 
                         type="primary" if st.session_state.current_page == page_name else "secondary"):
                st.session_state.current_page = page_name
                st.rerun()

        # Menu comum para todos os níveis
        menu_button("DASHBOARD", "📊", "DASHBOARD")
        
        # Central de contestação (Onde o SDR contesta e o Admin responde)
        label_cont = "MINHAS CONTESTAÇÕES" if nivel == "SDR" else "GESTÃO DE CONTESTAÇÕES"
        menu_button(label_cont, "⚖️", "CONTESTACAO")
        
        # Histórico com nomes diferentes dependendo do nível para clareza
        label_hist = "MEU HISTÓRICO" if nivel == "SDR" else "HISTÓRICO GERAL"
        menu_button(label_hist, "📜", "HISTORICO")

        # Menu Exclusivo Gestão (ADMIN)
        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("**Área do Gestor**")
            menu_button("MONITORIA", "📝", "MONITORIA")
            menu_button("CADASTRO SDR", "👥", "CADASTRO")

        st.divider()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_page = "DASHBOARD"
            st.rerun()

    # 3. Roteamento de Páginas e Proteção de Rotas
    page = st.session_state.current_page

    if page == "DASHBOARD":
        render_dashboard()

    elif page == "CONTESTACAO":
        # Esta função (em contestacao.py) agora contém a lógica de resposta do ADM
        render_contestacao()

    elif page == "HISTORICO":
        st.title(f"📜 {label_hist}")
        df = get_all_records_db()
        
        if not df.empty:
            if nivel == "SDR":
                # Filtro SDR: Vê apenas os seus registros
                df = df[df['sdr'] == st.session_state.user]
                st.info("Visualização de histórico pessoal (Somente Leitura)")
                
                # Colunas sugeridas para o SDR acompanhar no histórico
                cols = ["data", "nota", "contestada", "status_contestacao", "resposta_gestor"]
                # Exibe apenas as colunas que existem no DF para evitar erro
                df_display = df[[c for c in cols if c in df.columns]]
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                # ADMIN vê tudo
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum registro encontrado.")

    elif page == "MONITORIA":
        if nivel == "ADMIN":
            render_monitoria()
        else:
            st.error("Acesso Negado.")
            st.session_state.current_page = "DASHBOARD"

    elif page == "CADASTRO":
        if nivel == "ADMIN":
            render_cadastro()
        else:
            st.error("Acesso Negado.")
            st.session_state.current_page = "DASHBOARD"

if __name__ == "__main__":
    main()