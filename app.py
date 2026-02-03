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
    # Removido emoji do título
    st.title("Histórico de Monitorias")
    
    # Busca dados no banco
    df = get_all_records_db("monitorias")
    
    if df is not None and not df.empty:
        df['sdr_upper'] = df['sdr'].astype(str).str.strip().str.upper()
        
        # LOGICA: SDR vê só o dele. ADMIN e GESTAO veem filtro de busca.
        if nivel not in ["ADMIN", "GESTAO"]:
            df_exibicao = df[df['sdr_upper'] == nome_completo.upper()].copy()
        else:
            c_busca, _ = st.columns([1, 1])
            busca = c_busca.text_input("Pesquisar SDR:", placeholder="Digite o nome...")
            df_exibicao = df[df['sdr'].str.contains(busca, case=False)].copy() if busca else df.copy()

        if not df_exibicao.empty:
            # --- LÓGICA PARA EXTRAIR NC e NCG ---
            def extrair_falhas(detalhes):
                if not detalhes or not isinstance(detalhes, dict):
                    return "Nenhuma"
                falhas = [f"{k} ({v})" for k, v in detalhes.items() if v in ["NC", "NCG"]]
                return ", ".join(falhas) if falhas else "Tudo Conforme"

            # Criamos a nova coluna baseada no JSON de detalhes
            df_exibicao['Itens NC/NCG'] = df_exibicao['detalhes'].apply(extrair_falhas)

            # Tratamento de Data
            if 'criado_em' in df_exibicao.columns:
                df_exibicao['Data'] = pd.to_datetime(df_exibicao['criado_em']).dt.strftime('%d/%m/%Y %H:%M')
            else:
                df_exibicao['Data'] = "N/A"

            # Exibição da Tabela
            st.dataframe(
                df_exibicao[[
                    'Data', 
                    'sdr', 
                    'nota', 
                    'Itens NC/NCG', 
                    'monitor_responsavel', 
                    'observacoes'
                ]], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning("Nenhum registro encontrado.")
    else:
        st.info("O banco de dados está vazio.")

# --- MAIN ---
def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon="🚀")
    
    # CSS para garantir que a sidebar apareça
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {
                display: block !important;
                visibility: visible !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 1. Inicialização do CookieManager com chave fixa para estabilidade
    cookie_manager = stx.CookieManager(key="cookie_handler_main")

    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "logout_clicked" not in st.session_state: st.session_state.logout_clicked = False 
    if "current_page" not in st.session_state: st.session_state.current_page = "DASHBOARD"

    # 🔄 LÓGICA DE AUTO-LOGIN CORRIGIDA
    # Só tenta logar se o usuário NÃO estiver autenticado
    if not st.session_state.authenticated:
        time.sleep(0.1) # Pequena pausa para leitura correta do cookie
        cookie_user = cookie_manager.get('user_token')
        
        # CORREÇÃO: Verifica se o cookie existe E se não é vazio/inválido
        if cookie_user and str(cookie_user).strip() != "":
            try:
                res = supabase.table("usuarios").select("*").eq("user", cookie_user).single().execute()
                if res.data and res.data.get('esta_ativo', True):
                    user_data = res.data
                    st.session_state.authenticated = True
                    st.session_state.user_nome = user_data.get('nome', cookie_user)
                    st.session_state.user_login = user_data['user']
                    st.session_state.nivel = str(user_data.get('nivel', 'SDR')).upper()
                    st.session_state.foto_url = user_data.get('foto_url')
                    st.rerun() 
                else:
                    # Se o usuário não existe mais ou está inativo, limpa o cookie
                    cookie_manager.delete('user_token')
            except Exception:
                pass

    # 🔒 BLOQUEIO DE ACESSO
    if not st.session_state.authenticated:
        render_login(cookie_manager)
        st.stop()

    # ⏳ RENOVAÇÃO DO TEMPO (KEEP-ALIVE)
    # Se chegou aqui, está logado. Renovamos o token.
    if st.session_state.authenticated:
        new_expiry = datetime.now() + timedelta(minutes=60)
        cookie_manager.set('user_token', st.session_state.user_login, expires_at=new_expiry, key="renew_cookie")

    apply_custom_styles()
    nivel = st.session_state.nivel
    nome_completo = st.session_state.user_nome
    user_login = st.session_state.user_login

    # --- SIDEBAR ---
    with st.sidebar:
        foto_perfil = st.session_state.get('foto_url')
        if foto_perfil:
            st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:10px;'><img src='{foto_perfil}' style='width:100px;height:100px;border-radius:50%;object-fit:cover;border:2px solid white;'></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center;font-size:60px;'>👤</div>", unsafe_allow_html=True)

        st.markdown(f"<h3 style='text-align:center;'>{nome_completo}</h3>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align:center;'>{nivel}</p>", unsafe_allow_html=True)

        # Notificações
        num_notif = buscar_contagem_notificacoes(nome_completo, nivel)
        if num_notif > 0 and nivel != "GESTAO": 
            st.markdown(f"<div style='background:#1e1e1e;border:1px solid #ff4b4b;border-radius:12px;padding:12px;text-align:center;margin:15px 0;'><span style='font-size:28px;'>🔔</span><div style='color:#ff4b4b;font-weight:bold;'>{num_notif} Pendência(s)</div></div>", unsafe_allow_html=True)
            if st.button("Verificar Agora", use_container_width=True, type="primary"):
                limpar_todas_notificacoes(nome_completo)
                st.session_state.current_page = "CONTESTACAO"
                st.rerun()
        
        st.divider()

        # Função de Botão Simples
        def menu_btn(label, target):
            is_active = st.session_state.current_page == target
            if st.button(label, use_container_width=True, type="primary" if is_active else "secondary", key=f"nav_{target}"):
                st.session_state.current_page = target
                st.rerun()

        # --- MENU ---
        menu_btn("DASHBOARD", "DASHBOARD")
        
        if nivel == "SDR":
            menu_btn("CONTESTAR NOTA", "CONTESTACAO")
            menu_btn("MEUS RESULTADOS", "MEUS_RESULTADOS")
            menu_btn("HISTÓRICO", "HISTORICO")

        if nivel == "ADMIN":
            menu_btn("CONTESTAÇÕES", "CONTESTACAO")

        if nivel == "GESTAO":
            menu_btn("HISTÓRICO GERAL", "HISTORICO")
            menu_btn("RELATÓRIOS", "RELATORIOS")
            menu_btn("CADASTRAR USUÁRIO", "CADASTRO")

        menu_btn("MEU PERFIL", "PERFIL")

        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("### Administrativo")
            menu_btn("NOVA MONITORIA", "MONITORIA")
            menu_btn("CONFIG. CRITÉRIOS", "CONFIG_CRITERIOS")
            menu_btn("RELATÓRIOS", "RELATORIOS")
            menu_btn("GESTAO DE EQUIPE", "GESTAO_USUARIOS")
            menu_btn("CADASTRAR USUÁRIO", "CADASTRO")
            menu_btn("AUDITORIA", "AUDITORIA")

        st.divider()
        
        # --------------------------------------------------------------------
        # 2. LOGOUT BLINDADO (CORREÇÃO DO F5)
        # --------------------------------------------------------------------
        if st.button("Sair", use_container_width=True, key="logout_btn"):
            # a) Trava a sessão
            st.session_state.logout_clicked = True
            st.session_state.authenticated = False
            
            # b) Sobrescreve o cookie com valor vazio e expirado (NUCLEAR)
            # Isso é mais forte que o delete e funciona instantaneamente
            cookie_manager.set('user_token', "", expires_at=datetime.now() - timedelta(days=1))
            
            # c) Pausa estratégica para o navegador processar
            time.sleep(0.5)
            
            # d) Recarrega
            st.rerun()

    # --- ROTEAMENTO ---
    page = st.session_state.current_page
    try:
        if page == "DASHBOARD": render_dashboard()
        elif page == "PERFIL": render_meu_perfil()
        
        # SDR
        elif page == "CONTESTACAO" and nivel == "SDR": render_contestacao()
        elif page == "MEUS_RESULTADOS" and nivel == "SDR": render_meus_resultados()
        elif page == "HISTORICO" and nivel == "SDR": render_historico_geral(nivel, nome_completo)
        
        # ADMIN
        elif page == "CONTESTACAO" and nivel == "ADMIN": render_contestacao()
        
        # GESTAO (e compartilhadas)
        elif page == "HISTORICO" and nivel in ["ADMIN", "GESTAO"]: render_historico_geral(nivel, nome_completo)
        elif page == "RELATORIOS" and nivel == "GESTAO": render_relatorios()
        elif page == "CADASTRO" and nivel == "GESTAO": render_cadastro()
        
        # ADMIN Exclusivas
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