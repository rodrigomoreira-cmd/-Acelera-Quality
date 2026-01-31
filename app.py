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
from style import apply_custom_styles
from database import get_all_records_db, supabase, buscar_contagem_notificacoes, limpar_todas_notificacoes  

def main():
    # 1. Configuração inicial da página (Design Black)
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon="🚀")

    # Inicialização de variáveis de sessão
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"
    if "user_nome" not in st.session_state:
        st.session_state.user_nome = None

    # 2. Bloqueio de Acesso (Login)
    if not st.session_state.authenticated:
        render_login()
        st.stop()

    # Aplica os estilos CSS (Preto/Dark)
    apply_custom_styles()
    
    nivel = str(st.session_state.get('nivel', 'SDR')).upper()
    nome_completo = st.session_state.get('user_nome', 'Usuário') 
    user_login = st.session_state.get('user_login', '')

    # --- 3. BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        # Foto de Perfil
        try:
            res_foto = supabase.table("usuarios").select("foto_url").eq("user", user_login).single().execute()
            foto_url = res_foto.data.get('foto_url') if res_foto.data else None
            
            if foto_url:
                st.markdown(f"""
                    <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                        <img src="{foto_url}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 2px solid #ffffff;">
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align: center; font-size: 60px; margin-bottom: 10px;'>👤</div>", unsafe_allow_html=True)
        except:
            st.markdown("<div style='text-align: center; font-size: 60px; margin-bottom: 10px;'>👤</div>", unsafe_allow_html=True)

        st.markdown(f"<h3 style='text-align: center; margin-bottom: 0;'>{nome_completo}</h3>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align: center; margin-top: 0;'>{nivel}</p>", unsafe_allow_html=True)

       # --- CENTRAL DE NOTIFICAÇÕES (SININHO) ---
        num_notif = buscar_contagem_notificacoes(nome_completo, nivel)
        
        if num_notif > 0:
            # Card visual
            st.markdown(f"""
                <div style="background: linear-gradient(145deg, #1e1e1e, #141414); border: 1px solid #ff4b4b; border-radius: 12px; padding: 12px; text-align: center; margin: 15px 0; box-shadow: 0 4px 15px rgba(255, 75, 75, 0.2);">
                    <span style="font-size: 28px;">🔔</span>
                    <div style="color: #ff4b4b; font-weight: bold; font-size: 15px; margin-top: 5px;">
                        {num_notif} Pendência{"s" if num_notif > 1 else ""}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # --- A MÁGICA ACONTECE AQUI ---
            if st.button("Verificar e Limpar", use_container_width=True, key="quick_notif_btn", type="primary"):
                # 1. Limpa tudo no banco imediatamente
                limpar_todas_notificacoes(nome_completo)
                
                # 2. Redireciona para a página
                st.session_state.current_page = "CONTESTACAO"
                
                # 3. Recarrega a página (O sino vai sumir pois num_notif será 0)
                st.rerun()
        else:
            st.markdown("<p style='text-align: center; color: #555; font-size: 0.85em; margin-top: 10px;'>✅ Tudo em dia</p>", unsafe_allow_html=True)

        st.divider()

        # Botões de Navegação
        def menu_btn(label, icon, target):
            active = st.session_state.current_page == target
            if st.button(f"{icon} {label}", use_container_width=True, 
                         type="primary" if active else "secondary", 
                         key=f"nav_btn_{target}"):
                st.session_state.current_page = target
                st.rerun()

        menu_btn("DASHBOARD", "📊", "DASHBOARD")
        
        # Rótulo dinâmico, mas destino fixo na página que trata as contestações
        label_c = "CENTRAL DE JULGAMENTO" if nivel == "ADMIN" else "CONTESTAR NOTA"
        menu_btn(label_c, "⚖️", "CONTESTACAO")
        
        menu_btn("MEUS RESULTADOS", "📈", "MEUS_RESULTADOS")
        menu_btn("HISTÓRICO", "📜", "HISTORICO")
        menu_btn("MEU PERFIL", "👤", "PERFIL")

        # Botões Administrativos (Mantendo todos que você listou)
        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("### 🛠️ Administrativo")
            menu_btn("NOVA MONITORIA", "📝", "MONITORIA")
            menu_btn("CONFIG. CRITÉRIOS", "⚙️", "CONFIG_CRITERIOS")
            menu_btn("RELATÓRIOS", "📈", "RELATORIOS")
            menu_btn("GESTÃO DE EQUIPE", "👥", "GESTAO_USUARIOS")
            menu_btn("CADASTRO USUÁRIO", "👥", "CADASTRO")
            menu_btn("AUDITORIA", "🕵️", "AUDITORIA")

        st.divider()
        if st.button("🚪 Sair", use_container_width=True, key="logout_btn"):
            st.session_state.clear()
            st.rerun()

    # --- 4. ROTEAMENTO DE PÁGINAS ---
    page = st.session_state.current_page

    try:
        if page == "DASHBOARD": 
            render_dashboard()
        elif page == "PERFIL": 
            render_meu_perfil()
        elif page == "CONTESTACAO": 
            # CORREÇÃO CRÍTICA: O SDR também deve ir para render_contestacao para ver os avisos e contestar
            render_contestacao()
        elif page == "MEUS_RESULTADOS": 
            render_meus_resultados()
        elif page == "HISTORICO": 
            render_historico_geral(nivel, nome_completo)

        # Páginas Restritas ao ADMIN
        elif nivel == "ADMIN":
            if page == "MONITORIA": render_nova_monitoria()
            elif page == "CONFIG_CRITERIOS": render_gestao_criterios()
            elif page == "GESTAO_USUARIOS": render_usuario_gestao()
            elif page == "CADASTRO": render_cadastro()
            elif page == "AUDITORIA": render_auditoria()
            elif page == "RELATORIOS": render_relatorios()

    except Exception as e:
        st.error(f"Erro ao carregar {page}: {str(e)}")

def render_historico_geral(nivel, nome_completo):
    st.title("📜 Histórico de Monitorias")
    df = get_all_records_db("monitorias")
    
    if df is not None and not df.empty:
        # Padronização para filtro
        df['sdr_upper'] = df['sdr'].astype(str).str.strip().str.upper()
        
        if nivel != "ADMIN":
            df_exibicao = df[df['sdr_upper'] == nome_completo.upper()].copy()
        else:
            busca = st.text_input("🔍 Pesquisar por SDR:", placeholder="Digite o nome...")
            df_exibicao = df[df['sdr'].str.contains(busca, case=False)].copy() if busca else df.copy()

        if not df_exibicao.empty:
            df_exibicao['📅 Data'] = pd.to_datetime(df_exibicao['criado_em']).dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(
                df_exibicao[['📅 Data', 'sdr', 'nota', 'monitor_responsavel', 'observacoes']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "nota": st.column_config.NumberColumn("Nota", format="%.1f%%"),
                }
            )
        else:
            st.warning("Nenhum registro encontrado.")
    else:
        st.info("💡 O banco de dados está vazio.")

if __name__ == "__main__":
    main()