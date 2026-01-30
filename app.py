import streamlit as st
import pandas as pd
from auth import render_login
from dashboard import render_dashboard
from monitoria import render_nova_monitoria
from contestacao import render_contestacao
from cadastro import render_cadastro
from meus_resultados import render_meus_resultados 
from usuarios_gestao import render_usuario_gestao 
from meu_perfil import render_meu_perfil 
from auditoria import render_auditoria 
from relatorios import render_relatorios 
from gestao_criterios import render_gestao_criterios 
# Importação de funções do banco
from database import get_all_records_db, supabase, buscar_contagem_notificacoes
from style import apply_custom_styles

def main():
    # Configuração inicial da página
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon="🚀")

    # --- 1. INICIALIZAÇÃO DE SEGURANÇA (ESTADO DA SESSÃO) ---
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"
    if "user_nome" not in st.session_state:
        st.session_state.user_nome = "Usuário"
    if "nivel" not in st.session_state:
        st.session_state.nivel = "SDR"
    if "user_login" not in st.session_state:
        st.session_state.user_login = ""

    # --- 2. VERIFICAÇÃO DE AUTENTICAÇÃO ---
    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # Aplica estilos CSS personalizados
    apply_custom_styles()
    
    nivel = str(st.session_state.get('nivel', 'SDR')).upper()
    nome_completo = st.session_state.get('user_nome', 'Usuário') 

    # --- 3. BARRA LATERAL (MENU DE NAVEGAÇÃO) ---
    with st.sidebar:
        # Lógica de exibição da Foto de Perfil
        try:
            res_foto = supabase.table("usuarios").select("foto_url").eq("user", st.session_state.user_login).single().execute()
            foto_url = res_foto.data.get('foto_url') if res_foto.data else None
            
            if foto_url:
                st.markdown(f"""
                    <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                        <img src="{foto_url}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 2px solid #ff4b4b;">
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align: center; font-size: 60px; margin-bottom: 10px;'>👤</div>", unsafe_allow_html=True)
        except:
            st.markdown("<div style='text-align: center; font-size: 60px; margin-bottom: 10px;'>👤</div>", unsafe_allow_html=True)

        st.markdown(f"<h3 style='text-align: center; margin-top: 0;'>{nome_completo}</h3>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align: center;'>Acesso: {nivel}</p>", unsafe_allow_html=True)
        st.divider()

        # Contador de Notificações para o Menu
        num_notif = buscar_contagem_notificacoes(nome_completo, nivel)
        badge = f" ({num_notif})" if num_notif > 0 else ""

        def menu_button(label, icon, page_name, suffix=""):
            is_active = st.session_state.current_page == page_name
            if st.button(
                f"{icon} {label}{suffix}", 
                use_container_width=True, 
                key=f"nav_btn_{page_name}", 
                type="primary" if is_active else "secondary"
            ):
                st.session_state.current_page = page_name
                st.rerun()

        # Itens Comuns
        menu_button("DASHBOARD", "📊", "DASHBOARD")
        label_contestacao = "CENTRAL DE CONTESTAÇÃO" if nivel == "ADMIN" else "CONTESTAR NOTA"
        menu_button(label_contestacao, "⚖️", "CONTESTACAO", suffix=badge)
        menu_button("MEU PERFIL", "👤", "PERFIL")
        menu_button("HISTÓRICO", "📜", "HISTORICO")

        # Itens Exclusivos ADMIN
        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("### 🛠️ Administrativo")
            menu_button("NOVA MONITORIA", "📝", "MONITORIA")
            menu_button("CONFIG. CRITÉRIOS", "⚙️", "CONFIG_CRITERIOS")
            menu_button("RELATÓRIOS", "📈", "RELATORIOS")
            menu_button("GESTÃO DE EQUIPE", "🛠️", "GESTAO_USUARIOS")
            menu_button("CADASTRO USUÁRIO", "👥", "CADASTRO")
            menu_button("AUDITORIA", "🕵️", "AUDITORIA")

        st.divider()
        if st.button("🚪 Sair", use_container_width=True, key="logout_sidebar_btn"):
            st.session_state.authenticated = False
            st.session_state.clear()
            st.rerun()

    # --- 4. ROTEAMENTO DE PÁGINAS ---
    page = st.session_state.current_page

    try:
        if page == "DASHBOARD":
            render_dashboard()
        
        elif page == "PERFIL":
            render_meu_perfil() # Corrigido: Agora chama render_meu_perfil e não a gestão
        
        elif page == "CONTESTACAO":
            if nivel == "ADMIN":
                render_contestacao()
            else:
                render_meus_resultados()
        
        elif page == "HISTORICO":
            render_historico_geral(nivel, nome_completo)

        # Páginas Administrativas
        elif nivel == "ADMIN":
            if page == "RELATORIOS": render_relatorios()
            elif page == "GESTAO_USUARIOS": render_usuario_gestao()
            elif page == "MONITORIA": render_nova_monitoria()
            elif page == "CONFIG_CRITERIOS": render_gestao_criterios()
            elif page == "CADASTRO": render_cadastro()
            elif page == "AUDITORIA": render_auditoria()

    except Exception as e:
        st.error(f"Erro ao carregar a página {page}: {str(e)}")

def render_historico_geral(nivel, nome_completo):
    """Função para renderizar o histórico de monitorias."""
    st.title("📜 Histórico de Monitorias")
    df = get_all_records_db("monitorias")
    
    if df is not None and not df.empty:
        df['sdr'] = df['sdr'].astype(str).str.strip()
        df['nota'] = pd.to_numeric(df['nota'], errors='coerce')
        df['criado_em'] = pd.to_datetime(df['criado_em'])
        
        if nivel != "ADMIN":
            df_exibicao = df[df['sdr'].str.upper() == nome_completo.upper()].copy()
        else:
            busca = st.text_input("🔍 Pesquisar por SDR:", placeholder="Digite o nome...")
            df_exibicao = df[df['sdr'].str.contains(busca, case=False)].copy() if busca else df.copy()

        if not df_exibicao.empty:
            df_exibicao = df_exibicao.sort_values(by='criado_em', ascending=False)
            df_exibicao['📅 Data'] = df_exibicao['criado_em'].dt.strftime('%d/%m/%Y %H:%M')
            df_final = df_exibicao[['📅 Data', 'sdr', 'nota', 'monitor_responsavel', 'observacoes']]
            df_final.columns = ['📅 Data', '👤 SDR', '🎯 Nota (%)', '🕵️ Monitor', '📝 Observações']

            st.dataframe(
                df_final, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "🎯 Nota (%)": st.column_config.NumberColumn(format="%.1f%%"),
                    "📝 Observações": st.column_config.TextColumn(width="large")
                }
            )
        else:
            st.warning("Nenhum registro encontrado.")
    else:
        st.info("💡 O banco de dados está vazio.")

if __name__ == "__main__":
    main()