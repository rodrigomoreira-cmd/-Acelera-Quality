import streamlit as st
from database import supabase
import pandas as pd

def render_meus_resultados():
    st.title("🎯 Meus Resultados")
    nome_completo = st.session_state.get('user_nome', 'Usuário').strip()
    
    if not nome_completo or nome_completo == "Usuário":
        st.error("❌ Nome de usuário não identificado. Por favor, faça login novamente.")
        return

    st.info(f"📋 Exibindo monitorias para: **{nome_completo}**")

    try:
        res = supabase.table("monitorias")\
            .select("*")\
            .ilike("sdr", nome_completo)\
            .order("criado_em", desc=True)\
            .execute()
        monitorias = res.data
    except Exception as e:
        st.error(f"Erro ao buscar resultados: {e}")
        return

    if not monitorias:
        st.warning(f"🔎 Nenhuma monitoria encontrada para '{nome_completo}'.")
        return

    for mon in monitorias:
        id_mon = mon['id']
        nota = mon.get('nota', 0)
        data_br = pd.to_datetime(mon['criado_em']).strftime('%d/%m/%Y %H:%M')

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### Monitoria - {data_br}")
                st.caption(f"Protocolo: {id_mon}")
            with col2:
                cor_nota = "normal" if nota >= 90 else "inverse"
                st.metric("Nota Final", f"{nota}%", delta_color=cor_nota)

            # Visão simplificada: Mostra apenas o feedback, sem o JSON do checklist
            with st.expander("🔍 Ver Feedback e Status"):
                st.write("**Feedback do Monitor:**")
                st.info(mon.get('observacoes', 'Sem observações registradas.'))
                
                st.divider()
                
                # Status da Contestação
                try:
                    res_con = supabase.table("contestacoes").select("*").eq("monitoria_id", id_mon).execute()
                    contesta_dados = res_con.data
                except:
                    contesta_dados = []
                
                if contesta_dados:
                    c = contesta_dados[0]
                    st.markdown(f"**Status da Contestação:** `{c['status']}`")
                    if c.get('decisao_gestao'):
                        st.success(f"**Resultado:** {c['decisao_gestao']}")
                        st.write(f"**Parecer da Gestão:** {c.get('justificativa_gestao', '')}")
                else:
                    with st.form(key=f"form_contest_{id_mon}"):
                        motivo = st.text_area("Deseja contestar esta nota? Descreva o motivo:")
                        if st.form_submit_button("Enviar Contestação"):
                            if len(motivo) > 10:
                                supabase.table("contestacoes").insert({
                                    "monitoria_id": id_mon, "sdr": nome_completo, "motivo": motivo, "status": "Pendente"
                                }).execute()
                                st.success("🚀 Enviada!")
                                st.rerun()