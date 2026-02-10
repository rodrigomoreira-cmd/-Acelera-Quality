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
# 📜 FUNÇÃO HISTÓRICO (GLOBAL COM CONTESTAÇÃO E EXPIRAÇÃO)
# ==========================================================
def render_historico_geral(nivel, nome_completo):
    st.title("📚 Histórico Geral de Monitorias")
    
    if st.button("🔄 Atualizar Dados", help="Recarrega monitorias e contestações"):
        get_all_records_db.clear()
        st.rerun()

    # 1. Busca os dados de ambas as tabelas
    df_monitorias = get_all_records_db("monitorias")
    df_contestacoes = get_all_records_db("contestacoes")
    
    if df_monitorias is None or df_monitorias.empty:
        st.info("O banco de dados está vazio.")
        return

    # 2. Processamento de Cruzamento (Merge) para a Tabela
    df_monitorias['criado_em'] = pd.to_datetime(df_monitorias['criado_em'])
    
    if df_contestacoes is not None and not df_contestacoes.empty:
        df_cont_resumo = df_contestacoes[['monitoria_id', 'motivo', 'status', 'resposta_admin']].rename(
            columns={
                'motivo': 'Motivo SDR',
                'status': 'Situação',
                'resposta_admin': 'Resposta Auditor'
            }
        )
        df_exibicao = pd.merge(df_monitorias, df_cont_resumo, left_on='id', right_on='monitoria_id', how='left')
    else:
        df_exibicao = df_monitorias.copy()
        df_exibicao['Situação'] = "Nenhuma"
        df_exibicao['Motivo SDR'] = "-"
        df_exibicao['Resposta Auditor'] = "-"

    # 3. Formatação da Tabela Principal
    df_exibicao['Data_Exibicao'] = df_exibicao['criado_em'].dt.strftime('%d/%m/%Y %H:%M')
    df_exibicao['Contestada?'] = df_exibicao['Situação'].apply(lambda x: "⚠️ Sim" if pd.notnull(x) and x != "Nenhuma" else "✅ Não")
    
    # Filtros de visualização
    if nivel not in ["ADMIN", "GESTAO"]:
        df_exibicao = df_exibicao[df_exibicao['sdr'].str.upper() == nome_completo.upper()].copy()
    else:
        c_busca, _ = st.columns([1, 1])
        busca = c_busca.text_input("🔍 Pesquisar SDR ou ID:", placeholder="Digite o nome ou ID...")
        if busca:
            df_exibicao = df_exibicao[
                (df_exibicao['sdr'].str.contains(busca, case=False)) | 
                (df_exibicao['id'].astype(str).contains(busca))
            ].copy()

    # Exibe a tabela com as novas colunas de contestação
    st.dataframe(
        df_exibicao[[
            'id', 'Data_Exibicao', 'sdr', 'nota', 'monitor_responsavel', 
            'Contestada?', 'Situação', 'Motivo SDR', 'Resposta Auditor'
        ]], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "nota": st.column_config.ProgressColumn("Nota", format="%d%%", min_value=0, max_value=100),
            "Situação": st.column_config.SelectboxColumn("Status Contest.", options=["Pendente", "Aceita", "Recusada", "Nenhuma"])
        }
    )

    # --- ZONA ADMINISTRATIVA (CARDS COM VALIDADE) ---
    if nivel == "ADMIN":
        st.divider()
        st.subheader("🛠️ Gerenciar Registros (Anulação)")
        st.info("Monitorias podem ser anuladas em até **24 horas** após a criação.")

        # Definir tempo de validade (exemplo: 24 horas)
        prazo_horas = 24
        agora = datetime.now(df_monitorias['criado_em'].dt.tz) # Sincroniza timezone

        # Mostra apenas os últimos 10 para não poluir
        for _, row in df_exibicao.head(10).iterrows():
            # Cálculo de expiração
            data_criacao = row['criado_em']
            data_limite = data_criacao + timedelta(hours=prazo_horas)
            expirado = agora > data_limite
            
            # Formatação do Card
            with st.container(border=True):
                col_info, col_status, col_btn = st.columns([3, 2, 1])
                
                col_info.markdown(f"**ID {row['id']}** | {row['sdr']}\n\n{row['Data_Exibicao']}")
                
                # Coluna de Status da Validade
                if expirado:
                    col_status.error(f"❌ Expirado\n\nLimite: {data_limite.strftime('%d/%m %H:%M')}")
                else:
                    col_status.success(f"⏳ Válido\n\nExpira em: {data_limite.strftime('%d/%m %H:%M')}")
                
                # Botão de Anular (Desabilita se expirado para segurança, ou mantém se Admin tiver passe livre)
                if col_btn.button("🗑️ Anular", key=f"del_{row['id']}", use_container_width=True, disabled=expirado):
                    modal_anular(row['id'], row['sdr'])

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