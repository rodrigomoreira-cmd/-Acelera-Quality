import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria

# --- MODAL DE CONTESTAÇÃO (SDR) ---
# Aqui usamos 'if button', então o st.rerun() É NECESSÁRIO para fechar o modal e atualizar a tela
@st.dialog("📝 Abrir Contestação")
def dialog_contestar(dados, nome_sdr):
    st.markdown(f"**Monitoria de {pd.to_datetime(dados['criado_em']).strftime('%d/%m/%Y')}**")
    st.markdown(f"Nota Original: **{dados['nota']}%**")
    
    st.info(f"Feedback do Monitor:\n\n{dados.get('observacoes', 'Sem observações.')}")
    
    st.write("---")
    st.write("Qual o motivo da sua discordância?")
    motivo = st.text_area("Justificativa", height=150, placeholder="Ex: O cliente não solicitou X, por isso não ofertei...")
    
    col_b1, col_b2 = st.columns([1, 1])
    
    # Botão de Enviar (Lógica direta)
    if col_b2.button("Enviar Contestação", type="primary", use_container_width=True):
        if len(motivo) < 15:
            st.error("⚠️ Escreva pelo menos 15 caracteres.")
        else:
            try:
                res = supabase.table("contestacoes").insert({
                    "monitoria_id": dados['id'],
                    "sdr_nome": nome_sdr,
                    "motivo": motivo,
                    "status": "Pendente",
                    "visualizada": False
                }).execute()
                
                if res.data:
                    supabase.table("monitorias").update({"contestada": True}).eq("id", dados['id']).execute()
                    st.toast("✅ Contestação enviada!", icon="🚀")
                    st.rerun() # NECESSÁRIO AQUI para fechar o dialog
            except Exception as e:
                st.error(f"Erro: {e}")
    
    if col_b1.button("Cancelar", use_container_width=True):
        st.rerun() # Fecha o dialog

# --- CALLBACKS ADMIN ---
# Esta função é chamada via on_click. REMOVEMOS O ST.RERUN() DAQUI.
def callback_julgamento_admin(id_c, id_m, status, nota=None):
    parecer = st.session_state.get(f"parecer_adm_{id_c}", "").strip()
    
    # Validação simples: se não tiver parecer, não faz nada (e avisa no toast)
    if not parecer:
        st.toast("⚠️ Escreva o parecer antes de julgar.", icon="⚠️")
        return

    try:
        # Atualiza a contestação
        supabase.table("contestacoes").update({
            "status": status, "resposta_admin": parecer, "visualizada": False 
        }).eq("id", id_c).execute()
        
        # Se foi deferido, atualiza a nota da monitoria
        if status == "Deferido" and nota is not None:
            supabase.table("monitorias").update({"nota": nota}).eq("id", id_m).execute()
            
        registrar_auditoria("JULGAMENTO", "Sistema", f"{status} | ID: {id_m}")
        st.toast(f"✅ Julgado: {status}", icon="⚖️")
        
        # OBS: st.rerun() FOI REMOVIDO DAQUI pois o on_click já faz o refresh
        
    except Exception as e:
        st.error(f"Erro: {e}")

# --- RENDERIZAÇÃO ---
def render_contestacao():
    nivel = st.session_state.get('nivel', 'SDR').upper()
    nome_usuario = st.session_state.get('user_nome')

    if not nome_usuario:
        st.warning("Login necessário.")
        st.stop()

    if nivel == "SDR":
        render_view_sdr(nome_usuario)
    else:
        render_admin_view()

def render_view_sdr(nome_sdr):
    st.title("Central de Contestação")
    
    tab_novas, tab_hist = st.tabs(["📌 Disponíveis", "📂 Histórico"])
    
    # --- ABA 1: LISTA LIMPA ---
    with tab_novas:
        res = supabase.table("monitorias").select("*").eq("sdr", nome_sdr).eq("contestada", False).execute()
        
        if not res.data:
            st.markdown("""
                <div style="text-align: center; padding: 40px; color: #666;">
                    <h3>✨ Tudo limpo!</h3>
                    <p>Nenhuma monitoria pendente de análise.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            for dados in res.data:
                with st.container(border=True):
                    c_nota, c_info, c_action = st.columns([1, 4, 1.5], vertical_alignment="center")
                    
                    nota = dados['nota']
                    cor = "green" if nota >= 90 else "orange" if nota >= 70 else "red"
                    
                    with c_nota:
                        st.markdown(f"<h2 style='color: {cor}; margin: 0; text-align: center;'>{nota}%</h2>", unsafe_allow_html=True)
                    
                    with c_info:
                        data_fmt = pd.to_datetime(dados['criado_em']).strftime('%d/%m')
                        st.markdown(f"**Data:** {data_fmt} • **Monitor:** {dados.get('monitor_responsavel', 'N/A')}")
                        obs = dados.get('observacoes', '')
                        if len(obs) > 60:
                            st.caption(f"{obs[:60]}... (Ver completo ao contestar)")
                        else:
                            st.caption(obs if obs else "Sem observações.")

                    with c_action:
                        if st.button("Contestar", key=f"btn_open_{dados['id']}", use_container_width=True):
                            dialog_contestar(dados, nome_sdr)

    # --- ABA 2: HISTÓRICO ---
    with tab_hist:
        res_h = supabase.table("contestacoes").select("*").eq("sdr_nome", nome_sdr).order("criado_em", desc=True).execute()
        
        if res_h.data:
            for item in res_h.data:
                status = item['status']
                with st.status(f"{pd.to_datetime(item['criado_em']).strftime('%d/%m')} - Pedido {status}", state="complete" if status != "Pendente" else "running", expanded=False):
                    st.markdown(f"**Seu motivo:** {item['motivo']}")
                    st.divider()
                    if item.get('resposta_admin'):
                        st.markdown(f"**Parecer da Qualidade:**\n> {item['resposta_admin']}")
                    else:
                        st.caption("Aguardando análise da gestão...")
        else:
            st.caption("Nenhum registro encontrado.")

def render_admin_view():
    st.subheader("⚖️ Central de Julgamento")
    
    res = supabase.table("contestacoes").select("*, monitorias(*)").eq("status", "Pendente").execute()
    
    if not res.data:
        st.success("Tudo em dia.")
        return
        
    for c in res.data:
        mon = c.get('monitorias', {})
        
        with st.container(border=True):
            col_left, col_right = st.columns([1, 2])
            
            with col_left:
                st.markdown(f"### {c['sdr_nome']}")
                st.caption(f"Nota Original: {mon.get('nota')}%")
                st.warning(f"🗣️ {c['motivo']}")
            
            with col_right:
                parecer = st.text_area("Parecer:", key=f"parecer_adm_{c['id']}", height=80)
                nova_n = st.number_input("Nova Nota:", 0, 100, int(mon.get('nota', 0)), key=f"n_{c['id']}")
                
                c1, c2 = st.columns(2)
                
                # AQUI USAMOS ON_CLICK, ENTÃO O CALLBACK NÃO PODE TER ST.RERUN()
                c1.button("Deferir", on_click=callback_julgamento_admin, args=(c['id'], c['monitoria_id'], "Deferido", nova_n), type="primary", use_container_width=True, key=f"d_{c['id']}")
                c2.button("Indeferir", on_click=callback_julgamento_admin, args=(c['id'], c['monitoria_id'], "Indeferido"), use_container_width=True, key=f"i_{c['id']}")