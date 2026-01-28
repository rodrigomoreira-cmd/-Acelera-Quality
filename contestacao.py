import streamlit as st
from database import supabase, get_all_records_db

def render_contestacao():
    st.title("Central de Contestações")
    nivel = st.session_state.get('nivel', 'sdr')
    df = get_all_records_db("monitorias")

    if df.empty:
        st.info("Nenhuma monitoria registrada.")
        return

    # Filtro: SDR vê apenas as dele. Admin vê as contestadas pendentes.
    if nivel == "sdr":
        df_view = df[df['sdr'] == st.session_state.user]
    else:
        df_view = df[df['contestada'] == True]

    for _, row in df_view.iterrows():
        status = row.get('status_contestacao', 'Pendente')
        emoji = "🟠" if status == "Pendente" else "🟢" if status == "Deferido" else "🔴"
        
        with st.expander(f"{emoji} Monitoria {row['data']} | SDR: {row['sdr']} | Nota: {row['nota']}%"):
            # Visão do SDR
            if nivel == "sdr":
                if row.get('contestada'):
                    st.write(f"**Sua Contestação:** {row['motivo_contestacao']}")
                    if row.get('resposta_gestor'):
                        st.info(f"**Resposta do Gestor:** {row['resposta_gestor']} (Status: {status})")
                else:
                    with st.popover("CONTESTAR"):
                        motivo = st.text_area("Explique sua discordância:", key=f"m_{row['id']}")
                        if st.button("Enviar", key=f"b_{row['id']}"):
                            supabase.table("monitorias").update({
                                "contestada": True, "motivo_contestacao": motivo, "status_contestacao": "Pendente"
                            }).eq("id", row['id']).execute()
                            st.rerun()
            
            # Visão do ADMIN
            else:
                st.write(f"**Motivo do SDR:** {row['motivo_contestacao']}")
                with st.popover("RESPONDER"):
                    decisao = st.selectbox("Decisão", ["Deferido", "Indeferido"], key=f"d_{row['id']}")
                    resp = st.text_area("Justificativa:", key=f"r_{row['id']}")
                    if st.button("Salvar Decisão", key=f"f_{row['id']}"):
                        supabase.table("monitorias").update({
                            "status_contestacao": decisao, "resposta_gestor": resp
                        }).eq("id", row['id']).execute()
                        st.rerun()