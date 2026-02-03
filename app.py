import streamlit as st
import pandas as pd
import time
import extra_streamlit_components as stx 
from datetime import datetime, timedelta

# Importação das páginas
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

# --- FUNÇÃO AUXILIAR DE HISTÓRICO ---
def render_historico_geral(nivel, nome_completo):
    # (Mantenha sua função de histórico aqui exatamente como estava antes)
    st.title("📜 Histórico de Monitorias")
    df = get_all_records_db("monitorias")
    if df is not None and not df.empty:
        df['sdr_upper'] = df['sdr'].astype(str).str.strip().str.upper()
        if nivel != "ADMIN":
            df_exibicao = df[df['sdr_upper'] == nome_completo.upper()].copy()
        else:
            busca = st.text_input("🔍 Pesquisar por SDR:", placeholder="Digite o nome...")
            df_exibicao = df[df['sdr'].str.contains(busca, case=False)].copy() if busca else df.copy()

        if not df_exibicao.empty:
            if 'criado_em' in df_exibicao.columns:
                df_exibicao['📅 Data'] = pd.to_datetime(df_exibicao['criado_em']).dt.strftime('%d/%m/%Y %H:%M')
            else:
                df_exibicao['📅 Data'] = "N/A"
            st.dataframe(df_exibicao[['📅 Data', 'sdr', 'nota', 'monitor_responsavel', 'observacoes']], use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum registro encontrado.")
    else:
        st.info("O banco de dados está vazio.")

# --- MAIN ---
def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon="🚀")
    
    # Gerenciador de cookies
    cookie_manager = stx.CookieManager()

    # Inicialização de variáveis
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "logout_clicked" not in st.session_state:
        st.session_state.logout_clicked = False # Trava para o bug do logout

    # ---------------------------------------------------------
    # 🔄 LÓGICA DE AUTO-LOGIN (PERSISTÊNCIA)
    # ---------------------------------------------------------
    # Só tenta auto-logar se não estiver autenticado E se não acabou de clicar em sair
    if not st.session_state.authenticated and not st.session_state.logout_clicked:
        time.sleep(0.1) # Delay para ler cookie
        cookie_user = cookie_manager.get('user_token')
        
        if cookie_user:
            try:
                res = supabase.table("usuarios").select("*").eq("user", cookie_user).single().execute()
                if res.data and res.data.get('esta_ativo', True):
                    user_data = res.data
                    st.session_state.authenticated = True
                    st.session_state.user_nome = user_data.get('nome', cookie_user)
                    st.session_state.user_login = user_data['user']
                    st.session_state.nivel = str(user_data.get('nivel', 'SDR')).upper()
                    st.session_state.current_page = "DASHBOARD"
                    # Força rerun para aplicar o login visualmente na hora
                    st.rerun() 
                else:
                    cookie_manager.delete('user_token')
            except Exception:
                pass

    # ---------------------------------------------------------
    # 🔒 BLOQUEIO DE ACESSO
    # ---------------------------------------------------------
    if not st.session_state.authenticated:
        render_login(cookie_manager)
        st.stop()

    # =========================================================
    # ⏳ RENOVAÇÃO DO TEMPO (KEEP-ALIVE)
    # =========================================================
    # Se o usuário chegou aqui, ele está logado e ativo. 
    # Renovamos o cookie por mais 10 minutos.
    if st.session_state.authenticated:
        # Apenas renovamos se não estivermos no processo de logout
        if not st.session_state.logout_clicked:
            new_expiry = datetime.now() + timedelta(minutes=10)
            cookie_manager.set('user_token', st.session_state.user_login, expires_at=new_expiry, key="renew_cookie")

    # Aplica estilos e carrega dados
    apply_custom_styles()
    nivel = str(st.session_state.get('nivel', 'SDR')).upper()
    nome_completo = st.session_state.get('user_nome', 'Usuário')
    user_login = st.session_state.get('user_login', '')

    # --- SIDEBAR ---
    with st.sidebar:
        # Foto de Perfil
        try:
            res_foto = supabase.table("usuarios").select("foto_url").eq("user", user_login).single().execute()
            foto_url = res_foto.data.get('foto_url') if res_foto.data else None
            if foto_url:
                st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:10px;'><img src='{foto_url}' style='width:100px;height:100px;border-radius:50%;object-fit:cover;border:2px solid white;'></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align:center;font-size:60px;'>👤</div>", unsafe_allow_html=True)
        except:
            st.markdown("<div style='text-align:center;font-size:60px;'>👤</div>", unsafe_allow_html=True)

        st.markdown(f"<h3 style='text-align:center;'>{nome_completo}</h3>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align:center;'>{nivel}</p>", unsafe_allow_html=True)

        # Notificações
        num_notif = buscar_contagem_notificacoes(nome_completo, nivel)
        if num_notif > 0:
            st.markdown(f"<div style='background:#1e1e1e;border:1px solid #ff4b4b;border-radius:12px;padding:12px;text-align:center;margin:15px 0;'><span style='font-size:28px;'>🔔</span><div style='color:#ff4b4b;font-weight:bold;'>{num_notif} Pendência(s)</div></div>", unsafe_allow_html=True)
            if st.button("Verificar", use_container_width=True, type="primary"):
                limpar_todas_notificacoes(nome_completo)
                st.session_state.current_page = "CONTESTACAO"
                st.rerun()
        
        st.divider()

        # Menu
        def menu_btn(label, icon, target):
            active = st.session_state.current_page == target
            if st.button(f"{icon} {label}", use_container_width=True, type="primary" if active else "secondary", key=f"nav_{target}"):
                st.session_state.current_page = target
                st.rerun()

        menu_btn("DASHBOARD", "📊", "DASHBOARD")
        menu_btn("CENTRAL DE JULGAMENTO" if nivel == "ADMIN" else "CONTESTAR NOTA", "⚖️", "CONTESTACAO")
        menu_btn("MEUS RESULTADOS", "📈", "MEUS_RESULTADOS")
        menu_btn("HISTÓRICO", "📜", "HISTORICO")
        menu_btn("MEU PERFIL", "👤", "PERFIL")

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
        
        # --- LOGOUT CORRIGIDO ---
        if st.button("🚪 Sair", use_container_width=True, key="logout_btn"):
            # 1. Marca que clicou em sair para travar o auto-login
            st.session_state.logout_clicked = True
            # 2. Deleta o cookie
            cookie_manager.delete('user_token')
            # 3. Limpa a sessão
            st.session_state.authenticated = False
            # 4. Recarrega a página (vai cair no render_login)
            st.rerun()

    # --- ROTEAMENTO ---
    page = st.session_state.current_page
    try:
        if page == "DASHBOARD": render_dashboard()
        elif page == "PERFIL": render_meu_perfil()
        elif page == "CONTESTACAO": render_contestacao()
        elif page == "MEUS_RESULTADOS": render_meus_resultados()
        elif page == "HISTORICO": render_historico_geral(nivel, nome_completo)
        elif nivel == "ADMIN":
            if page == "MONITORIA": render_nova_monitoria()
            elif page == "CONFIG_CRITERIOS": render_gestao_criterios()
            elif page == "GESTAO_USUARIOS": render_usuario_gestao()
            elif page == "CADASTRO": render_cadastro()
            elif page == "AUDITORIA": render_auditoria()
            elif page == "RELATORIOS": render_relatorios()
        else:
            render_dashboard()
    except Exception as e:
        st.error(f"Erro ao carregar {page}: {str(e)}")

if __name__ == "__main__":
    main()