import streamlit as st
import pandas as pd
import time
import extra_streamlit_components as stx 
from datetime import datetime, timedelta

# ==========================================================
# 📦 IMPORTAÇÕES DE MÓDULOS
# ==========================================================
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

# Adicionado 'anular_monitoria' na importação
from database import get_all_records_db, supabase, buscar_contagem_notificacoes, limpar_todas_notificacoes, anular_monitoria

# ==========================================================
# 🛑 MODAL DE CONFIRMAÇÃO DE ANULAÇÃO
# ==========================================================
@st.dialog("🗑️ Confirmar Anulação")
def modal_anular(id_mon):
    st.warning(f"Tem a certeza que deseja excluir permanentemente a monitoria ID: {id_mon}?")
    st.markdown("""
        <small style='color: #ff4b4b;'>
        ⚠️ Esta ação removerá a nota do cálculo de média e apagará quaisquer contestações associadas.
        </small>
    """, unsafe_allow_html=True)
    
    motivo = st.text_input("Motivo obrigatório para auditoria:", placeholder="Ex: Monitoria duplicada / Erro de sistema")
    
    col_a, col_b = st.columns(2)
    if col_a.button("Confirmar Exclusão", type="primary", use_container_width=True):
        if not motivo or len(motivo) < 5:
            st.error("Escreva um motivo válido (min. 5 letras).")
        else:
            sucesso, msg = anular_monitoria(id_mon, motivo)
            if sucesso:
                st.success("Registro removido!")
                time.sleep(1.0)
                st.rerun()
            else:
                st.error(f"Erro: {msg}")
    
    if col_b.button("Cancelar", use_container_width=True):
        st.rerun()

# ==========================================================
# 📜 FUNÇÃO HISTÓRICO (GLOBAL)
# ==========================================================
def render_historico_geral(nivel, nome_completo):
    st.title("Histórico de Monitorias")
    
    # Botão para forçar atualização do cache se necessário
    if st.button("🔄 Atualizar Tabela", help="Recarrega os dados do banco"):
        get_all_records_db.clear()
        st.rerun()

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
            def extrair_falhas(detalhes):
                if not detalhes or not isinstance(detalhes, dict): return "Nenhuma"
                falhas = [f"{k} ({v})" for k, v in detalhes.items() if v in ["NC", "NCG"]]
                return ", ".join(falhas) if falhas else "✅ 100% Conforme"

            df_exibicao['Itens NC/NCG'] = df_exibicao['detalhes'].apply(extrair_falhas)
            
            if 'criado_em' in df_exibicao.columns:
                df_exibicao['Data'] = pd.to_datetime(df_exibicao['criado_em']).dt.strftime('%d/%m/%Y %H:%M')
            else:
                df_exibicao['Data'] = "N/A"

            # Exibe a tabela
            st.dataframe(
                df_exibicao[['id', 'Data', 'sdr', 'nota', 'Itens NC/NCG', 'monitor_responsavel', 'observacoes']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "nota": st.column_config.ProgressColumn("Nota", format="%d%%", min_value=0, max_value=100)
                }
            )

            # --- ZONA ADMINISTRATIVA (APENAS ADMIN VÊ) ---
            if nivel == "ADMIN":
                st.divider()
                st.markdown("### 🛠️ Gerir Registos (Admin)")
                with st.expander("🗑️ Área de Risco: Anular Monitoria"):
                    st.warning("Atenção: A anulação é irreversível.")
                    
                    # Selectbox com os IDs visíveis na tabela acima
                    lista_ids = df_exibicao['id'].unique()
                    id_selecionado = st.selectbox("Selecione o ID da monitoria para anular:", options=lista_ids)
                    
                    if st.button(f"Solicitar Anulação da Monitoria #{id_selecionado}", type="secondary"):
                        modal_anular(id_selecionado)

        else:
            st.warning("Nenhum registro encontrado.")
    else:
        st.info("O banco de dados está vazio.")

# ==========================================================
# 🚀 FUNÇÃO PRINCIPAL (MAIN)
# ==========================================================
def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon="🚀")
    
    # CSS para garantir visibilidade da sidebar
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {
                display: block !important;
                visibility: visible !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 1. Inicialização do CookieManager
    cookie_manager = stx.CookieManager(key="cookie_handler_main")

    # 2. Inicialização de estados fundamentais
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "logout_clicked" not in st.session_state: st.session_state.logout_clicked = False 
    if "current_page" not in st.session_state: st.session_state.current_page = "DASHBOARD"
    
    # --- TRAVA DE SEGURANÇA: LIMPEZA NO STARTUP ---
    if "app_init" not in st.session_state:
        st.session_state.app_init = True

    # --- LÓGICA DE AUTO-LOGIN BLINDADA (RESOLVE O F5) ---
    if not st.session_state.authenticated and not st.session_state.logout_clicked:
        # Tenta ler o cookie
        cookie_user = cookie_manager.get('user_token')
        
        # Se o cookie não veio de primeira (comum no F5), esperamos um pouco e tentamos de novo
        if cookie_user is None:
            time.sleep(0.6)  # Tempo necessário para o componente JS carregar no browser
            cookie_user = cookie_manager.get('user_token')

        # Se agora temos um cookie válido (e não vazio)
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
                    # Usuário inativo ou inválido, mata o cookie
                    cookie_manager.set('user_token', "", expires_at=datetime.now() - timedelta(days=1))
            except Exception:
                pass

    # 3. BLOQUEIO DE ACESSO
    if not st.session_state.authenticated:
        render_login(cookie_manager)
        st.stop()

    # --- RENOVAÇÃO / KEEP-ALIVE (Inatividade de 10 minutos) ---
    # Só renova se o usuário NÃO clicou em sair
    if not st.session_state.logout_clicked:
        new_expiry = datetime.now() + timedelta(minutes=10)
        cookie_manager.set(
            'user_token', 
            st.session_state.user_login, 
            expires_at=new_expiry, 
            key="renew_session"
        )

    apply_custom_styles()
    nivel = st.session_state.nivel
    nome_completo = st.session_state.user_nome

    # --- SIDEBAR ---
    with st.sidebar:
        # Perfil Visual
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

        if nivel in ["ADMIN", "GESTAO"]:
            menu_btn("HISTÓRICO GERAL", "HISTORICO")
            menu_btn("RELATÓRIOS", "RELATORIOS")
            menu_btn("CADASTRAR USUÁRIO", "CADASTRO")

        menu_btn("MEU PERFIL", "PERFIL")

        if nivel == "ADMIN":
            st.markdown("---")
            st.markdown("### Administrativo")
            menu_btn("NOVA MONITORIA", "MONITORIA")
            menu_btn("CONFIG. CRITÉRIOS", "CONFIG_CRITERIOS")
            menu_btn("GESTAO DE EQUIPE", "GESTAO_USUARIOS")
            menu_btn("AUDITORIA", "AUDITORIA")

        st.divider()
        
        # --- LOGOUT DEFINITIVO ---
        if st.button("Sair", use_container_width=True, key="logout_btn"):
            st.session_state.logout_clicked = True
            st.session_state.authenticated = False
            # NUCLEAR: Sobrescreve o cookie com valor vazio e expira no passado
            cookie_manager.set('user_token', "", expires_at=datetime.now() - timedelta(days=1))
            time.sleep(0.5)
            st.rerun()

    # --- ROTEAMENTO ---
    page = st.session_state.current_page
    try:
        if page == "DASHBOARD": render_dashboard()
        elif page == "PERFIL": render_meu_perfil()
        elif page == "CONTESTACAO": render_contestacao()
        elif page == "MEUS_RESULTADOS" and nivel == "SDR": render_meus_resultados()
        
        # A função agora está no escopo global e pode ser chamada
        elif page == "HISTORICO": render_historico_geral(nivel, nome_completo)
        
        elif page == "RELATORIOS": render_relatorios()
        elif page == "CADASTRO": render_cadastro()
        elif page == "MONITORIA": render_nova_monitoria()
        elif page == "GESTAO_USUARIOS": render_usuario_gestao()
        elif page == "CONFIG_CRITERIOS": render_gestao_criterios()
        elif page == "AUDITORIA": render_auditoria()
        else: render_dashboard()
    except Exception as e:
        st.error(f"Erro ao carregar {page}: {str(e)}")

if __name__ == "__main__":
    main()