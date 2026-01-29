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
    # 1. Configuração Inicial da Página
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    # 2. Gerenciamento de Estado de Sessão
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    # 3. Bloqueio de Segurança (Login)
    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # 4. Aplicação do Estilo Visual (CSS Customizado)
    apply_custom_styles()

    # Identificação do Nível de Acesso (SDR ou ADMIN)
    nivel = st.session_state.get('nivel', 'sdr').upper()

    # 5. Sidebar com Navegação Corrigida
    with st.sidebar:
        nome_usuario = st.session_state.get('user', 'Usuário')
        st.markdown(f"### 👤 {nome_usuario}")
        st.write(f"Nível: {nivel}")
        st.divider()

        # Função de menu atualizada com 'key' única para evitar erro de ID duplicado
        def menu_button(label, icon, page_name):
            if st.button(
                f"{icon} {label}", 
                use_container_width=True, 
                key=f"sidebar_btn_{page_name}", # Resolve o erro da imagem 6f6b12
                type="primary" if st.session_state.current_page == page_name else "secondary"
            ):
                st.session_state.current_page = page_name
                st.rerun()

        # MENU PARA TODOS (SDR e ADMIN) - Passando os 3 argumentos corretamente
        menu_button("DASHBOARD", "📊", "DASHBOARD")
        menu_button("MEU PERFIL", "👤", "PERFIL")
        menu_button("CONTESTAR NOTA", "⚖️", "CONTESTACAO")
        menu_button("HISTÓRICO", "📜", "HISTORICO")

        # MENU ADICIONAL PARA ADMIN
        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("**Gestão de Equipe**")
            menu_button("NOVA MONITORIA", "📝", "MONITORIA")
            menu_button("CADASTRO SDR", "👥", "CADASTRO")

        st.divider()
        # Botão de Sair com chave única
        if st.button("🚪 Sair", use_container_width=True, key="sidebar_logout_btn"):
            st.session_state.authenticated = False
            st.rerun()

    # 6. Roteamento de Páginas (Lógica de Exibição)
    page = st.session_state.current_page

    try:
        if page == "DASHBOARD":
            render_dashboard()
        
        elif page == "PERFIL":
            render_usuario_gestao() # Nova tela de alteração de senha e dados
        
        elif page == "CONTESTACAO":
            render_contestacao() 
        
        elif page == "HISTORICO":
            st.title("📜 Histórico de Monitorias")
            df = get_all_records_db("monitorias") 
            
            if df is not None and not df.empty:
                if nivel == "SDR":
                    # Filtra apenas as monitorias do usuário logado
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

    except KeyError as e:
        # Tratamento para os erros de Secrets das imagens 6fc872 e 6f72b9
        st.error(f"⚠️ Erro de configuração: A chave {e} não foi encontrada nas Secrets.")
        st.info("Verifique se o SUPABASE_URL e SUPABASE_KEY estão configurados no painel do Streamlit.")

if __name__ == "__main__":
    main()