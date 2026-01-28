import streamlit as st
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_monitoria
from cadastro import render_cadastro
from contestacao import render_contestacao
from database import get_all_records_db
from style import apply_custom_styles  

def main():
    # 1. Configuração Inicial da Página
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    # 2. Gerenciamento de Estado de Sessão
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    # 3. Bloqueio de Login
    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # 4. Aplicação do Estilo Visual Personalizado (Gradientes)
    apply_custom_styles()

    # Identificação do Nível de Acesso
    nivel = st.session_state.get('nivel', 'sdr').upper()

    # 5. Sidebar com Navegação Estilizada
    with st.sidebar:
        # Verificação de segurança para o nome do usuário
        nome_usuario = st.session_state.get('user', 'Usuário')
        st.markdown(f"### 👤 {nome_usuario}")
        st.write(f"Nível: {nivel}")
        st.divider()

        # Definição da função com 3 parâmetros
        def menu_button(label, icon, page_name):
            if st.button(f"{icon} {label}", use_container_width=True, 
                         type="primary" if st.session_state.current_page == page_name else "secondary"):
                st.session_state.current_page = page_name
                st.rerun()

        # MENU PARA SDR - Agora com os 3 argumentos corretos
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

    # 6. Roteamento de Páginas
    page = st.session_state.current_page

    if page == "DASHBOARD":
        render_dashboard()
    
    elif page == "CONTESTACAO":
        render_contestacao() 
    
    elif page == "HISTORICO":
        st.title("📜 Histórico de Monitorias")
        # Importante: Verifique se get_all_records_db aceita o nome da tabela como argumento
        df = get_all_records_db("monitorias") 
        
        if df is not None and not df.empty:
            if nivel == "SDR":
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