import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria

# --- CALLBACKS (Lógica de Execução) ---

def marcar_lida(tabela, item_id):
    """Atualiza o status de visualização para limpar notificações."""
    try:
        supabase.table(tabela).update({"visualizada": True}).eq("id", item_id).execute()
    except Exception as e:
        st.error(f"Erro ao atualizar visualização: {e}")

def callback_enviar_contestacao(dados_mon, nome_sdr):
    """Processa o envio da contestação pelo SDR."""
    justificativa = st.session_state.get(f"input_just_{dados_mon['id']}", "").strip()
    
    if len(justificativa) < 15:
        st.session_state['msg_contest'] = ("erro", "⚠️ A justificativa deve conter pelo menos 15 caracteres para ser analisada.")
        return

    try:
        # 1. Insere na tabela de contestações
        res = supabase.table("contestacoes").insert({
            "monitoria_id": dados_mon['id'],
            "sdr_nome": nome_sdr,
            "justificativa": justificativa,
            "status": "Pendente",
            "visualizada": False
        }).execute()
        
        if res.data:
            # 2. Marca a monitoria como 'contestada' para não aparecer na lista de novas
            supabase.table("monitorias").update({"contestada": True}).eq("id", dados_mon['id']).execute()
            st.session_state['msg_contest'] = ("sucesso", "✅ Contestação enviada! Aguarde a revisão do ADMIN.")
            
            # Limpa o campo de texto após enviar
            st.session_state[f"input_just_{dados_mon['id']}"] = ""
    except Exception as e:
        st.session_state['msg_contest'] = ("erro", f"Erro ao enviar: {e}")

def callback_julgamento_admin(id_c, id_m, status, nota=None):
    """Processa o veredito do Administrador."""
    parecer = st.session_state.get(f"parecer_adm_{id_c}", "").strip()
    if not parecer:
        st.session_state['msg_admin'] = ("erro", "⚠️ É obrigatório escrever um parecer para o SDR.")
        return
    try:
        # 1. Atualiza a contestação
        supabase.table("contestacoes").update({
            "status": status, 
            "resposta_admin": parecer, 
            "visualizada": False 
        }).eq("id", id_c).execute()
        
        # 2. Se deferido, atualiza a nota na monitoria original
        if status == "Deferido" and nota is not None:
            supabase.table("monitorias").update({"nota": nota}).eq("id", id_m).execute()
        
        registrar_auditoria("JULGAMENTO CONTESTAÇÃO", "Sistema", f"Status: {status} | ID Monitoria: {id_m}")
        st.session_state['msg_admin'] = ("sucesso", f"✅ Julgamento registrado como {status}!")
    except Exception as e:
        st.session_state['msg_admin'] = ("erro", f"Erro ao julgar: {e}")

# --- RENDERIZAÇÃO ---

def render_contestacao():
    nivel = st.session_state.get('nivel', 'SDR').upper()
    nome_usuario = st.session_state.get('user_nome')

    if nivel == "SDR":
        # 1. NOTIFICAÇÕES (Sininho)
        res_mon = supabase.table("monitorias").select("*").eq("sdr", nome_usuario).eq("visualizada", False).execute()
        res_cont = supabase.table("contestacoes").select("*").eq("sdr_nome", nome_usuario).neq("status", "Pendente").eq("visualizada", False).execute()

        if res_mon.data or res_cont.data:
            st.markdown("### 🔔 Novidades")
            for m in res_mon.data:
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    c1.info(f"✨ Nova Monitoria Disponível | Nota: {m['nota']}%")
                    c2.button("OK", key=f"v_mon_{m['id']}", on_click=marcar_lida, args=("monitorias", m['id']))
            
            for n in res_cont.data:
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    cor = "green" if n['status'] == "Deferido" else "red"
                    c1.markdown(f"⚖️ Resultado de Contestação: **:{cor}[{n['status']}]**\n\n*Parecer: {n['resposta_admin']}*")
                    c2.button("OK", key=f"v_cont_{n['id']}", on_click=marcar_lida, args=("contestacoes", n['id']))
            st.divider()

        render_abas_sdr(nome_usuario)
    else:
        render_admin_view()

def render_abas_sdr(nome_sdr):
    tab1, tab2 = st.tabs(["🆕 Nova Contestação", "📜 Meu Histórico"])
    
    with tab1:
        if 'msg_contest' in st.session_state:
            t, txt = st.session_state.pop('msg_contest')
            if t == "sucesso": st.success(txt); st.balloons()
            else: st.error(txt)
            
        res = supabase.table("monitorias").select("*").eq("sdr", nome_sdr).eq("contestada", False).execute()
        if not res.data:
            st.info("Você não possui monitorias pendentes de contestação.")
        else:
            opcoes = {f"Data: {r['criado_em'][:10]} | Nota Atual: {r['nota']}%": r for r in res.data}
            sel = st.selectbox("Selecione a monitoria para contestar:", ["Selecione..."] + list(opcoes.keys()))
            
            if sel != "Selecione...":
                dados = opcoes[sel]
                with st.container(border=True):
                    st.markdown(f"**Feedback do Monitor:**\n> {dados.get('observacoes')}")
                    st.text_area("Sua justificativa (seja específico):", key=f"input_just_{dados['id']}", height=150)
                    st.button("🚀 Enviar para Revisão", on_click=callback_enviar_contestacao, args=(dados, nome_sdr), type="primary", use_container_width=True)

    with tab2:
        res_h = supabase.table("contestacoes").select("*").eq("sdr_nome", nome_sdr).order("criado_em", desc=True).execute()
        if res_h.data:
            df = pd.DataFrame(res_h.data)
            df['criado_em'] = pd.to_datetime(df['criado_em']).dt.strftime('%d/%m/%Y')
            st.dataframe(df[['criado_em', 'status', 'resposta_admin', 'justificativa']], use_container_width=True, hide_index=True)
        else:
            st.info("Você ainda não realizou nenhuma contestação.")

def render_admin_view():
    st.subheader("⚖️ Central de Julgamento")
    if 'msg_admin' in st.session_state:
        t, txt = st.session_state.pop('msg_admin')
        if t == "sucesso": st.success(txt)
        else: st.error(txt)

    # Busca contestações pendentes e traz os dados da monitoria relacionada (Join)
    res = supabase.table("contestacoes").select("*, monitorias(*)").eq("status", "Pendente").execute()
    
    if not res.data:
        st.success("✅ Nenhuma contestação pendente no momento!")
        return

    for c in res.data:
        mon = c.get('monitorias', {})
        with st.container(border=True):
            col_info, col_voto = st.columns([3, 2])
            
            with col_info:
                st.markdown(f"### SDR: {c['sdr_nome']}")
                st.markdown(f"**Nota Original:** {mon.get('nota')}%")
                st.warning(f"**Argumento do SDR:**\n\n{c['justificativa']}")
            
            with col_voto:
                st.text_area("Parecer do Julgador:", key=f"parecer_adm_{c['id']}", placeholder="Explique o motivo do aceite ou recusa...")
                nova_n = st.number_input("Ajustar Nota para:", 0, 100, int(mon.get('nota', 0)), key=f"n_{c['id']}")
                
                c1, c2 = st.columns(2)
                c1.button("✅ Deferir", on_click=callback_julgamento_admin, args=(c['id'], c['monitoria_id'], "Deferido", nova_n), use_container_width=True, type="primary")
                c2.button("❌ Indeferir", on_click=callback_julgamento_admin, args=(c['id'], c['monitoria_id'], "Indeferido"), use_container_width=True)