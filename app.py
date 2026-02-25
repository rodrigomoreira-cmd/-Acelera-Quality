import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

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
from matriz_decisao import render_pdi  
from style import apply_custom_styles
from database import get_all_records_db, supabase, buscar_contagem_notificacoes, limpar_todas_notificacoes, anular_monitoria_auditada, registrar_auditoria, remover_evidencia_monitoria

# ==========================================================
# 🔔 MODAL DE NOTIFICAÇÕES
# ==========================================================
@st.dialog("🔔 Central de Notificações")
def modal_notificacoes(nome_usuario):
    st.markdown("Acompanhe os seus avisos, resultados de PDI e contestações:")
    try:
        # Busca apenas as não lidas para limpar a visão
        res = supabase.table("notificacoes").select("*").eq("usuario", nome_usuario).eq("lida", False).execute()
        notifs = res.data if res.data else []
        
        if not notifs:
            st.info("🎉 Você não tem notificações no momento.")
        else:
            notifs = sorted(notifs, key=lambda x: x.get('id', 0), reverse=True)
            
            for n in notifs:
                cor_borda = "#ff4b4b"
                icone = "🔴"
                msg = n.get('mensagem', 'Nova notificação')
                
                st.markdown(f"""
                    <div style='padding:12px; border-left:4px solid {cor_borda}; margin-bottom:8px; background-color:rgba(255,255,255,0.05); border-radius:5px;'>
                        <span style='font-size:14px; color:white;'>{icone} {msg}</span>
                    </div>
                """, unsafe_allow_html=True)
            
        st.divider()
        
        c_limpar, c_lidas, c_fechar = st.columns(3)
        
        if c_lidas.button("✅ Lidas", use_container_width=True):
            supabase.table("notificacoes").update({"lida": True}).eq("usuario", nome_usuario).execute()
            st.rerun()
            
        if c_limpar.button("🗑️ Limpar", use_container_width=True):
            limpar_todas_notificacoes(nome_usuario)
            st.rerun()
            
        if c_fechar.button("❌ Fechar", use_container_width=True):
            st.rerun()
                
    except Exception as e:
        st.error(f"Erro ao carregar notificações: {e}")

# ==========================================================
# MODAL DE ANULAR AUDITORIA
# ==========================================================
@st.dialog("🗑️ Confirmar Anulação")
def modal_anular(id_mon, sdr_nome):
    st.warning(f"Deseja excluir permanentemente a monitoria de **{sdr_nome}**?")
    st.markdown("<small style='color: #ff4b4b;'>⚠️ Esta ação removerá a nota do cálculo de média e apagará as fotos anexadas.</small>", unsafe_allow_html=True)
    motivo = st.text_input("Motivo obrigatório para auditoria:")
    
    col_a, col_b = st.columns(2)
    if col_a.button("Confirmar Exclusão", type="primary", use_container_width=True):
        if not motivo or len(motivo) < 5: st.error("Escreva um motivo válido.")
        else:
            quem_esta_logado = st.session_state.get('user_nome', 'Admin Desconhecido')
            sucesso, msg = anular_monitoria_auditada(id_mon, motivo, quem_esta_logado)
            if sucesso:
                st.success("Registro removido e arquivos apagados da nuvem!")
                time.sleep(1.5)
                st.rerun()
            else: st.error(f"Erro: {msg}")
    
    if col_b.button("Cancelar", use_container_width=True): st.rerun()

def render_historico_geral(nivel, nome_completo):
    dept_selecionado = st.session_state.get('departamento_selecionado', 'Todos')
    st.title(f"📚 Histórico Consolidado - {dept_selecionado}")
    
    if st.button("🔄 Atualizar Dados"):
        get_all_records_db.clear()
        st.rerun()

    df_monitorias = get_all_records_db("monitorias")
    df_contestacoes = get_all_records_db("contestacoes")
    
    if df_monitorias is None or df_monitorias.empty:
        st.info("Nenhuma monitoria encontrada.")
        return

    df_monitorias['id'] = df_monitorias['id'].astype(str).str.strip()
    df_monitorias['criado_em'] = pd.to_datetime(df_monitorias['criado_em'])
    df_monitorias = df_monitorias.sort_values(by='criado_em', ascending=False)
    
    if df_contestacoes is not None and not df_contestacoes.empty:
        df_contestacoes['id'] = df_contestacoes['id'].astype(str).str.strip()
        df_contestacoes['monitoria_id'] = df_contestacoes['monitoria_id'].astype(str).str.strip()
        df_cont_resumo = df_contestacoes[['monitoria_id', 'status', 'resposta_admin']].rename(columns={'status': 'Situação'})
        df_exibicao = pd.merge(df_monitorias, df_cont_resumo, left_on='id', right_on='monitoria_id', how='left')
    else:
        df_exibicao = df_monitorias.copy()
        df_exibicao['Situação'] = "Nenhuma"

    if dept_selecionado != "Todos" and 'departamento' in df_exibicao.columns:
        df_exibicao = df_exibicao[df_exibicao['departamento'].astype(str).str.strip().str.upper() == dept_selecionado.strip().upper()].copy()

    df_exibicao['Data'] = df_exibicao['criado_em'].dt.strftime('%d/%m/%Y %H:%M')
    
    # ==========================================================
    # 🛡️ REGRA DE SEGURANÇA: OCULTAR ADMIN MESTRE
    # ==========================================================
    if nivel != "ADMIN":
        df_exibicao = df_exibicao[
            (df_exibicao['sdr'] != 'admin@grupoacelerador.com.br') & 
            (df_exibicao['monitor_responsavel'] != 'admin@grupoacelerador.com.br')
        ].copy()

    if nivel not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
        df_exibicao = df_exibicao[df_exibicao['sdr'].str.strip().str.upper() == nome_completo.strip().upper()].copy()
    else:
        c_busca, _ = st.columns([1, 1])
        busca = c_busca.text_input("🔍 Pesquisar Colaborador:")
        if busca: df_exibicao = df_exibicao[df_exibicao['sdr'].str.contains(busca, case=False, na=False)].copy()

    if df_exibicao.empty:
        st.info("Nenhum dado encontrado.")
        return

    st.dataframe(
        df_exibicao[['Data', 'sdr', 'nota', 'monitor_responsavel', 'Situação']], 
        use_container_width=True, hide_index=True,
        column_config={"nota": st.column_config.ProgressColumn("Nota", format="%d%%", min_value=0, max_value=100)}
    )

    st.divider()
    st.subheader("🔍 Ver Detalhes da Monitoria")
    
    opcoes_hist = {f"📅 {row['Data']} | SDR: {row['sdr']} | Nota: {row['nota']}%": row['id'] for _, row in df_exibicao.iterrows()}
    escolha = st.selectbox("Escolha a Avaliação:", [""] + list(opcoes_hist.keys()))
    
    if escolha:
        id_sel = opcoes_hist[escolha]
        linha = df_exibicao[df_exibicao['id'] == id_sel].iloc[0]
        auditor_nome = linha['monitor_responsavel']

        try:
            res_aud = supabase.table("usuarios").select("foto_url").eq("nome", auditor_nome).execute()
            foto_auditor = res_aud.data[0].get('foto_url') if res_aud.data else None
        except: foto_auditor = None

        with st.container(border=True):
            c_f, c_t = st.columns([1, 4])
            with c_f:
                if foto_auditor: st.markdown(f'<img src="{foto_auditor}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid #ff4b4b;">', unsafe_allow_html=True)
                else: st.markdown('<div style="font-size: 60px;">🕵️</div>', unsafe_allow_html=True)
            with c_t:
                st.markdown(f"#### Avaliador: {auditor_nome}")
                st.markdown(f"**Avaliado:** {linha['sdr']} | **Nota:** `{linha['nota']}%`")
            
            if linha.get('observacoes'): st.info(f"💬 **Feedback:** {linha['observacoes']}")
            
            c_l1, c_l2 = st.columns(2)
            if linha.get('link_selene'): c_l1.markdown(f"🔗 [Gravação Selene]({linha['link_selene']})")
            if linha.get('link_nectar'): c_l2.markdown(f"🗂️ [Card CRM Nectar]({linha['link_nectar']})")

        st.markdown("### 📋 Detalhamento")
        detalhes = linha.get('detalhes')
        if detalhes and isinstance(detalhes, dict):
            for pergunta, info in detalhes.items():
                if isinstance(info, dict):
                    nota_c = info.get('nota', 'NSA')
                    coment = info.get('comentario', 'Sem comentário.')
                    tem_anexo = info.get('evidencia_anexada', False)
                    url_img = info.get('url_arquivo')
                    nome_arq = info.get('arquivo', 'Anexo')

                    if nota_c == "C": st.success(f"✅ **{pergunta}**")
                    elif nota_c in ["NC", "NGC", "NC Grave"]:
                        with st.expander(f"❌ {pergunta} (Penalidade: {nota_c})", expanded=True):
                            st.write(f"**Motivo:** {coment}")
                            if tem_anexo:
                                if url_img:
                                    st.image(url_img, caption=f"Evidência: {nome_arq}", use_container_width=True)
                                    col_link, col_btn = st.columns([3, 1])
                                    col_link.markdown(f"🔗 [Abrir Imagem Original]({url_img})")
                                    if nivel in ["ADMIN", "AUDITOR"]:
                                        if col_btn.button("🗑️ Apagar Foto", key=f"del_img_{id_sel}_{pergunta}", help="Remove a imagem da nuvem"):
                                            sucesso, msg = remover_evidencia_monitoria(id_sel, pergunta, url_img, nome_completo)
                                            if sucesso:
                                                st.success("✅ " + msg)
                                                time.sleep(1)
                                                st.rerun()
                                            else: st.error("❌ " + msg)
                                else: st.warning("⚠️ O arquivo foi registado, mas a URL falhou.")
                    else: st.markdown(f"➖ **{pergunta}** (NSA)")
                    
        if nivel == "ADMIN":
            st.divider()
            if st.button("🗑️ Excluir esta Auditoria", type="primary", use_container_width=True):
                modal_anular(id_sel, linha['sdr'])

def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon="🚀")
    st.markdown("<style>section[data-testid='stSidebar'] { display: block !important; visibility: visible !important; }</style>", unsafe_allow_html=True)

    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "departamento_selecionado" not in st.session_state: st.session_state.departamento_selecionado = "Todos"
    if "current_page" not in st.session_state: st.session_state.current_page = "DASHBOARD"

    if not st.session_state.authenticated:
        render_login()
        st.stop()

    apply_custom_styles()
    
    nivel = st.session_state.nivel
    nome_completo = st.session_state.user_nome
    meu_dept = st.session_state.get('departamento', nivel)

    with st.sidebar:
        foto_p = st.session_state.get('foto_url')
        if foto_p: st.markdown(f"<div style='text-align:center;'><img src='{foto_p}' style='width:90px;height:90px;border-radius:50%;object-fit:cover;border:2px solid #ff4b4b;'></div>", unsafe_allow_html=True)
        else: st.markdown("<div style='text-align:center;font-size:50px;'>👤</div>", unsafe_allow_html=True)

        if nivel == "ADMIN": rotulo_perfil = "ADMINISTRADOR"
        elif nivel == "GERENCIA": rotulo_perfil = "GERÊNCIA"
        else: rotulo_perfil = meu_dept

        st.markdown(f"<h3 style='text-align:center; margin-bottom: 0;'>{nome_completo}</h3>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; margin-top: 5px; margin-bottom: 15px;'><span style='background-color: #ff4b4b22; color: #ff4b4b; padding: 4px 15px; border-radius: 20px; font-size: 13px; font-weight: bold; border: 1px solid #ff4b4b44; text-transform: uppercase;'>{rotulo_perfil}</span></div>", unsafe_allow_html=True)
        st.divider()
        
        # ==========================================================
        # 🏢 TRAVA DE VISÃO POR DEPARTAMENTO
        # ==========================================================
        st.markdown("**🏢 Visão por Departamento**")
        
        if nivel == "GESTAO":
            # Trava Izabela/Gestão para ver apenas o próprio time e bloqueia o select
            st.session_state.departamento_selecionado = meu_dept
            st.selectbox("Filtrar sistema para:", [meu_dept], index=0, disabled=True)
            st.info(f"Visualizando Equipe: **{meu_dept}**")
        elif nivel in ["ADMIN", "AUDITOR", "GERENCIA"]:
            # Admin, Gerência e Auditor possuem visão global
            opcoes_d = ["Todos", "SDR", "Especialista", "Venda de Ingresso", "Auditor"]
            st.session_state.departamento_selecionado = st.selectbox(
                "Filtrar sistema para:", 
                opcoes_d, 
                index=opcoes_d.index(st.session_state.departamento_selecionado) if st.session_state.departamento_selecionado in opcoes_d else 0
            )
        else:
            # SDR normal também fica travado no próprio dept no background
            st.session_state.departamento_selecionado = meu_dept

        # ==========================================================
        # 🔔 GATILHO DO MODAL DE NOTIFICAÇÕES
        # ==========================================================
        res_n = buscar_contagem_notificacoes(nome_completo, nivel)
        qtd_notificacoes = int(res_n if res_n else 0)
        
        if nivel not in ["GESTAO", "GERENCIA"]: 
            # Define o tipo de botão (Vermelho chamativo se tiver pendência)
            tipo_btn = "primary" if qtd_notificacoes > 0 else "secondary"
            texto_btn = f"🔔 {qtd_notificacoes} Nova(s) Notificação(ões)" if qtd_notificacoes > 0 else "🔔 Notificações"
            
            if st.button(texto_btn, use_container_width=True, type=tipo_btn):
                # Ao clicar, abre o modal de notificações sem mudar de página
                modal_notificacoes(nome_completo)
                
        st.divider()

        # ==========================================================
        # 🕹️ LÓGICA DE MENUS E HIERARQUIA
        # ==========================================================
        def menu(label, target):
            if st.button(label, use_container_width=True, type="primary" if st.session_state.current_page == target else "secondary"):
                st.session_state.current_page = target
                st.rerun()

        menu("📊 DASHBOARD", "DASHBOARD")
        
        # 1. VISÃO DO SDR / ESPECIALISTA / VENDA DE INGRESSO
        if nivel not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            menu("⚖️ CONTESTAR NOTA", "CONTESTACAO")
            menu("📈 MEUS RESULTADOS", "MEUS_RESULTADOS")
            menu("📚 HISTÓRICO", "HISTORICO")
            menu("🎯 MEU PDI", "PDI")  
            
        # 2. VISÃO DA LIDERANÇA / TÉCNICO
        else:
            # MONITORIA e CONTESTAÇÃO: Apenas Admin, Gerência e Auditor
            if nivel in ["ADMIN", "GERENCIA", "AUDITOR"]:
                menu("📝 NOVA MONITORIA", "MONITORIA")
                menu("⚖️ CONTESTAÇÕES", "CONTESTACAO")
            
            # HISTÓRICO GERAL: Todos os níveis de liderança vêm
            menu("📚 HISTÓRICO GERAL", "HISTORICO")
            
            # RELATÓRIOS: Admin, Gerência e Auditor e Gestão
            if nivel in ["ADMIN", "GERENCIA", "AUDITOR", "GESTAO"]:
                menu("📋 RELATÓRIOS", "RELATORIOS")
            
            # MATRIZ DE DECISÃO (PDI): Apenas Admin, Gerência e Gestão
            if nivel in ["ADMIN", "GERENCIA", "GESTAO"]:
                menu("🎯 MATRIZ DE DECISÃO", "PDI") 
            
            # CONFIGURAÇÃO DE CRITÉRIOS: Apenas Admin e Auditor
            if nivel in ["ADMIN", "AUDITOR"]:
                menu("⚙️ CONFIG. CRITÉRIOS", "CONFIG_CRITERIOS")
            
            # GESTÃO DE USUÁRIOS: Admin e Gerência
            if nivel in ["ADMIN", "GERENCIA"]:
                menu("👤 CADASTRAR USUÁRIO", "CADASTRO")
                menu("👥 GESTÃO DE EQUIPE", "GESTAO_USUARIOS")
                
            # AUDITORIA DO SISTEMA: Exclusivo Admin
            if nivel == "ADMIN":
                st.markdown("---")
                menu("🕵️ AUDITORIA", "AUDITORIA")
        
        menu("👤 MEU PERFIL", "PERFIL")

        st.divider()
        
        if st.session_state.get('logout_step'):
            st.warning("🔐 Deseja sair do sistema?")
            col_conf, col_canc = st.columns(2)
            if col_conf.button("Confirmar Saída", type="primary", use_container_width=True):
                nome_saindo = st.session_state.get('user_nome', 'Desconhecido')
                registrar_auditoria("LOGOUT", "Sessão encerrada.", "N/A", nome_saindo)
                st.session_state.clear()
                st.rerun()
                
            if col_canc.button("Cancelar", use_container_width=True):
                st.session_state.logout_step = False
                st.rerun()
        else:
            if st.button("Sair do Sistema", use_container_width=True):
                st.session_state.logout_step = True
                st.rerun()

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
        elif page == "PDI": render_pdi() 
    except Exception as e:
        st.error(f"Erro ao carregar página: {e}")

if __name__ == "__main__":
    main()