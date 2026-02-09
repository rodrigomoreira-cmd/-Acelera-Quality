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

from database import (
    get_all_records_db, 
    supabase, 
    buscar_contagem_notificacoes, 
    limpar_todas_notificacoes, 
    anular_monitoria_auditada
)

# ==========================================================
# 🛑 MODAL DE CONFIRMAÇÃO DE ANULAÇÃO (CORRIGIDO)
# ==========================================================
@st.dialog("🗑️ Confirmar Anulação")
def modal_anular(id_mon, sdr_nome):
    st.warning(f"Deseja excluir permanentemente a monitoria de **{sdr_nome}** (ID: {id_mon})?")
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
            # --- PEGA QUEM ESTÁ LOGADO (EX: DANIEL) ---
            quem_esta_logado = st.session_state.get('user_nome', 'Admin Desconhecido')

            # --- ENVIA OS 3 PARÂMETROS ---
            sucesso, msg = anular_monitoria_auditada(id_mon, motivo, quem_esta_logado)
            
            if sucesso:
                st.success("Registro removido e auditado!")
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
    st.title("📚 Histórico de Monitorias")
    
    if st.button("🔄 Atualizar Tabela", help="Recarrega os dados do banco"):
        get_all_records_db.clear()
        st.rerun()

    df = get_all_records_db("monitorias")
    
    if df is not None and not df.empty:
        # Formata Data (Vem ISO do banco, converte para BR)
        df['criado_em'] = pd.to_datetime(df['criado_em'])
        df['Data_Exibicao'] = df['criado_em'].dt.strftime('%d/%m/%Y %H:%M')
        
        # Filtros de visualização
        if nivel not in ["ADMIN", "GESTAO"]:
            df_exibicao = df[df['sdr'].str.upper() == nome_completo.upper()].copy()
        else:
            c_busca, _ = st.columns([1, 1])
            busca = c_busca.text_input("🔍 Pesquisar SDR:", placeholder="Digite o nome...")
            df_exibicao = df[df['sdr'].str.contains(busca, case=False)].copy() if busca else df.copy()

        if not df_exibicao.empty:
            def extrair_falhas(detalhes):
                if not detalhes or not isinstance(detalhes, dict): return "Nenhuma"
                falhas = [f"{k}" for k, v in detalhes.items() if v in ["NC", "NC Grave"]]
                return ", ".join(falhas) if falhas else "✅ 100% Conforme"

            df_exibicao['Falhas'] = df_exibicao['detalhes'].apply(extrair_falhas)
            
            # Tabela Principal
            st.dataframe(
                df_exibicao[['id', 'Data_Exibicao', 'sdr', 'nota', 'Falhas', 'monitor_responsavel']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "nota": st.column_config.ProgressColumn("Nota", format="%d%%", min_value=0, max_value=100)
                }
            )

            # --- ZONA ADMINISTRATIVA (CARDS DE ANULAÇÃO) ---
            if nivel == "ADMIN":
                st.divider()
                st.subheader("🛠️ Gerenciar Registros (Admin)")
                st.info("Abaixo estão as monitorias recentes. Clique em 'Anular' para remover.")
                
                # Exibe lista para facilitar a exclusão
                for _, row in df_exibicao.head(10).iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"**ID {row['id']}** | {row['sdr']} | {row['Data_Exibicao']} | Nota: **{row['nota']}%**")
                        
                        # Passamos o ID e o Nome para o modal
                        if c2.button("🗑️ Anular", key=f"btn_del_{row['id']}", use_container_width=True):
                            modal_anular(row['id'], row['sdr'])

        else:
            st.warning("Nenhum registro encontrado.")
    else:
        st.info("O banco de dados está vazio.")

# ==========================================================
# 🚀 FUNÇÃO PRINCIPAL (MAIN)
# ==========================================================
def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon="🚀")
    
    # CSS Sidebar Fix
    st.markdown("<style>section[data-testid='stSidebar'] { display: block !important; visibility: visible !important; }</style>", unsafe_allow_html=True)

    cookie_manager = stx.CookieManager(key="cookie_handler_main")

    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "logout_clicked" not in st.session_state: st.session_state.logout_clicked = False 
    if "current_page" not in st.session_state: st.session_state.current_page = "DASHBOARD"
    if "app_init" not in st.session_state: st.session_state.app_init = True

    # --- AUTO-LOGIN ---
    if not st.session_state.authenticated and not st.session_state.logout_clicked:
        cookie_user = cookie_manager.get('user_token')
        if cookie_user is None:
            time.sleep(0.5)
            cookie_user = cookie_manager.get('user_token')

        if cookie_user and str(cookie_user).strip() != "":
            try:
                # Usa ILIKE para evitar erros de login salvo em maiúsculo/minúsculo
                res = supabase.table("usuarios").select("*").ilike("user", cookie_user).execute()
                if res.data and len(res.data) > 0:
                    user_data = res.data[0]
                    if user_data.get('esta_ativo', True):
                        st.session_state.authenticated = True
                        st.session_state.user_nome = user_data.get('nome')
                        st.session_state.user_login = user_data['user']
                        st.session_state.nivel = str(user_data.get('nivel', 'SDR')).upper()
                        st.session_state.foto_url = user_data.get('foto_url')
                        st.rerun() 
            except Exception: pass

    if not st.session_state.authenticated:
        render_login(cookie_manager)
        st.stop()

    # Renovação de Sessão
    if not st.session_state.logout_clicked:
        cookie_manager.set('user_token', st.session_state.user_login, expires_at=datetime.now() + timedelta(minutes=10), key="renew_session")

    apply_custom_styles()
    nivel = st.session_state.nivel
    nome_completo = st.session_state.user_nome

    # --- SIDEBAR ---
    with st.sidebar:
        foto_perfil = st.session_state.get('foto_url')
        if foto_perfil:
            st.markdown(f"<div style='text-align:center;'><img src='{foto_perfil}' style='width:90px;height:90px;border-radius:50%;object-fit:cover;border:2px solid #ff4b4b;'></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align:center;font-size:50px;'>👤</div>", unsafe_allow_html=True)

        st.markdown(f"<h3 style='text-align:center;'>{nome_completo}</h3>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align:center;'>{nivel}</p>", unsafe_allow_html=True)

        # Notificações
        num_notif = buscar_contagem_notificacoes(nome_completo, nivel)
        if num_notif > 0 and nivel != "GESTAO": 
            if st.button(f"🔔 {num_notif} Pendências", use_container_width=True, type="primary"):
                limpar_todas_notificacoes(nome_completo)
                st.session_state.current_page = "CONTESTACAO"
                st.rerun()
        
        st.divider()

        def menu_btn(label, target):
            if st.button(label, use_container_width=True, type="primary" if st.session_state.current_page == target else "secondary"):
                st.session_state.current_page = target
                st.rerun()

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
            menu_btn("NOVA MONITORIA", "MONITORIA")
            menu_btn("CONFIG. CRITÉRIOS", "CONFIG_CRITERIOS")
            menu_btn("GESTAO DE EQUIPE", "GESTAO_USUARIOS")
            menu_btn("AUDITORIA", "AUDITORIA") # <-- Botão adicionado e roteamento corrigido

        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state.logout_clicked = True
            st.session_state.authenticated = False
            cookie_manager.set('user_token', "", expires_at=datetime.now() - timedelta(days=1))
            st.rerun()

    # --- ROTEAMENTO FINAL ---
    page = st.session_state.current_page
    try:
        if page == "DASHBOARD": render_dashboard()
        elif page == "PERFIL": render_meu_perfil()
        elif page == "CONTESTACAO": render_contestacao()
        elif page == "MEUS_RESULTADOS": render_meus_resultados()
        elif page == "HISTORICO": render_historico_geral(nivel, nome_completo)
        elif page == "RELATORIOS": render_relatorios()
        elif page == "CADASTRO": render_cadastro()
        elif page == "MONITORIA": render_nova_monitoria()
        elif page == "GESTAO_USUARIOS": render_usuario_gestao()
        elif page == "CONFIG_CRITERIOS": render_gestao_criterios()
        elif page == "AUDITORIA": render_auditoria()
    except Exception as e:
        st.error(f"Erro ao carregar página: {e}")

if __name__ == "__main__":
    main()