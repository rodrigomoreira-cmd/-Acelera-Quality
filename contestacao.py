import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from database import supabase

# ==========================================================
# 🛑 POPUP DE FEEDBACK (NOVO)
# ==========================================================
@st.dialog("🔔 Resposta da Gestão")
def exibir_feedback_gestao(contestacao_id, status, resposta):
    st.markdown(f"### Status: {'✅ Aprovado' if status == 'Aprovado' else '🚫 Rejeitado'}")
    st.write(f"**Mensagem da Gestão:**")
    st.info(resposta if resposta else "Sem justificativa detalhada.")
    st.divider()
    if st.button("OK, entendi!", use_container_width=True, type="primary"):
        try:
            # Marca como visualizada para o popup não aparecer novamente
            supabase.table("contestacoes").update({"visualizada": True}).eq("id", contestacao_id).execute()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao confirmar: {e}")

# ==========================================================
# 🛑 MODAL DE CRIAÇÃO (MANTIDO)
# ==========================================================
@st.dialog("📝 Nova Contestação")
def abrir_modal_contestacao(monitoria_id, sdr_nome, nota, data_monitoria, obs_monitor):
    st.caption("Preencha os detalhes abaixo para enviar para análise da gestão.")
    
    c1, c2 = st.columns(2)
    c1.metric("Nota Original", f"{nota}%")
    c2.markdown(f"**Data:** {data_monitoria}<br>**Monitor:** {obs_monitor.split('|')[0] if '|' in obs_monitor else 'Gestão'}", unsafe_allow_html=True)
    
    st.info(f"🔎 **Observação:** {obs_monitor}")

    with st.form("form_modal_contestacao"):
        motivo = st.text_area("Motivo da Contestação:", placeholder="Explique detalhadamente...", height=150)
        enviar = st.form_submit_button("🚀 Enviar Contestação", type="primary", use_container_width=True)

        if enviar:
            if len(motivo) < 10:
                st.warning("⚠️ O motivo deve ter pelo menos 10 caracteres.")
            else:
                try:
                    payload = {
                        "monitoria_id": monitoria_id,
                        "sdr_nome": sdr_nome,
                        "motivo": motivo,
                        "status": "Pendente",
                        "visualizada": False 
                    }
                    supabase.table("contestacoes").insert(payload).execute()
                    supabase.table("monitorias").update({"contestada": True}).eq("id", monitoria_id).execute()
                    st.success("Enviado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

# ==========================================================
# 🖥️ RENDERIZAÇÃO DA PÁGINA PRINCIPAL
# ==========================================================
def render_contestacao():
    st.title("⚖️ Central de Contestação")

    nivel = st.session_state.get('nivel', 'SDR').upper()
    usuario_nome = st.session_state.get('user_nome', '')

    # ----------------------------------------------------------
    # VISÃO DO SDR
    # ----------------------------------------------------------
    if nivel == "SDR":
        # --- VERIFICA SE HÁ RESPOSTAS PARA MOSTRAR NO POPUP ---
        try:
            res_feedback = supabase.table("contestacoes").select("*")\
                .eq("sdr_nome", usuario_nome)\
                .eq("visualizada", False)\
                .neq("status", "Pendente")\
                .execute()
            
            if res_feedback.data:
                f = res_feedback.data[0]
                exibir_feedback_gestao(f['id'], f['status'], f['resposta_admin'])
        except:
            pass

        st.subheader("Minhas Monitorias Recentes")
        
        try:
            res = supabase.table("monitorias").select("*")\
                .eq("sdr", usuario_nome)\
                .eq("contestada", False)\
                .order("criado_em", desc=True)\
                .execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error("Erro ao conectar ao banco.")
            return

        if df.empty:
            st.info("🎉 Nenhuma monitoria pendente para contestação.")
            return

        for index, row in df.iterrows():
            with st.container(border=True):
                try:
                    data_obj = pd.to_datetime(row['criado_em']).replace(tzinfo=None)
                except:
                    data_obj = datetime.now()

                data_str = data_obj.strftime('%d/%m/%Y %H:%M')
                
                # --- LÓGICA DE DATA DE EXPIRAÇÃO (3 DIAS) ---
                data_expiracao = data_obj + timedelta(days=3)
                agora = datetime.now()
                expirado = agora > data_expiracao

                c1, c2, c3 = st.columns([1, 3, 1.5])
                
                with c1:
                    st.metric("Nota", f"{row['nota']}%")
                
                with c2:
                    st.markdown(f"**Realizada em:** {data_str}")
                    st.markdown(f"**Monitor:** {row['monitor_responsavel']}")
                    # EXIBIÇÃO DA DATA DE EXPIRAÇÃO
                    if expirado:
                        st.markdown(f"<span style='color:#ff4b4b;'>🔴 **Expirou em:** {data_expiracao.strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:#00cc96;'>🟢 **Expira em:** {data_expiracao.strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)

                with c3:
                    if expirado:
                        st.button("Prazo Excedido", disabled=True, key=f"exp_{row['id']}", use_container_width=True)
                    else:
                        if st.button("Contestar 📝", key=f"btn_{row['id']}", use_container_width=True, type="primary"):
                            abrir_modal_contestacao(
                                monitoria_id=row['id'],
                                sdr_nome=usuario_nome,
                                nota=row['nota'],
                                data_monitoria=data_str,
                                obs_monitor=row.get('observacoes', '')
                            )

    # ----------------------------------------------------------
    # VISÃO DO ADMIN / GESTÃO
    # ----------------------------------------------------------
    elif nivel in ["ADMIN", "GESTAO"]:
        st.subheader("Gerenciar Contestações")
        status_filter = st.radio("Status:", ["Pendente", "Aprovado", "Rejeitado"], horizontal=True)
        
        try:
            res = supabase.table("contestacoes").select("*").eq("status", status_filter).order("criado_em", desc=True).execute()
            df_cont = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except:
            st.error("Erro de conexão.")
            return

        if df_cont.empty:
            st.info(f"Nenhuma contestação {status_filter}.")
            return

        for index, row in df_cont.iterrows():
            with st.expander(f"{row['sdr_nome']} | {pd.to_datetime(row['criado_em']).strftime('%d/%m')}", expanded=(status_filter=="Pendente")):
                st.write(f"**Motivo:** {row['motivo']}")
                
                if status_filter == "Pendente":
                    with st.form(key=f"julgar_{row['id']}"):
                        resp = st.text_area("Resposta da Gestão:")
                        c_ok, c_no = st.columns(2)
                        
                        aprovado = c_ok.form_submit_button("✅ Aceitar", use_container_width=True)
                        rejeitado = c_no.form_submit_button("🚫 Rejeitar", use_container_width=True)

                        if aprovado:
                            supabase.table("contestacoes").update({
                                "status": "Aprovado", 
                                "resposta_admin": resp,
                                "data_resolucao": datetime.now().isoformat(),
                                "visualizada": False
                            }).eq("id", row['id']).execute()
                            st.success("Aprovado!"); time.sleep(1); st.rerun()
                            
                        if rejeitado:
                            supabase.table("contestacoes").update({
                                "status": "Rejeitado", 
                                "resposta_admin": resp,
                                "data_resolucao": datetime.now().isoformat(),
                                "visualizada": False
                            }).eq("id", row['id']).execute()
                            st.error("Rejeitado!"); time.sleep(1); st.rerun()
                else:
                    st.write(f"**Gestão:** {row.get('resposta_admin')}")