import streamlit as st
from database import supabase, get_all_records_db

def render_contestacao():
    st.title("⚖️ Central de Contestações")
    nivel = st.session_state.get('nivel', 'sdr').upper()
    
    df = get_all_records_db("monitorias")
    if df.empty:
        st.info("Nenhuma monitoria encontrada.")
        return

    # Filtro lógico
    if nivel == "SDR":
        df_view = df[df['sdr'] == st.session_state.user]
    else:
        df_view = df[df['contestada'] == True]

    for _, row in df_view.iterrows():
        status = row.get('status_contestacao', 'Pendente')
        with st.expander(f"Monitoria {row['data']} | Nota: {row['nota']}% | Status: {status}"):
            
            # Lógica para o SDR
            if nivel == "SDR":
                if row['contestada']:
                    st.warning(f"Sua justificativa: {row['motivo_contestacao']}")
                    if row.get('resposta_gestor'):
                        st.info(f"Resposta do Gestor: {row['resposta_gestor']}")
                else:
                    with st.popover("Contestar esta nota"):
                        motivo = st.text_area("Descreva o motivo", key=f"m_{row['id']}")
                        if st.button("Enviar", key=f"b_{row['id']}"):
                            supabase.table("monitorias").update({
                                "contestada": True, "motivo_contestacao": motivo, "status_contestacao": "Pendente"
                            }).eq("id", row['id']).execute()
                            st.rerun()

            # Lógica para o ADMIN
            else:
                st.write(f"**SDR:** {row['sdr']}")
                st.write(f"**Motivo do SDR:** {row['motivo_contestacao']}")
                with st.popover("Responder"):
                    decisao = st.selectbox("Decisão", ["Deferido", "Indeferido"], key=f"d_{row['id']}")
                    resp = st.text_area("Sua resposta", key=f"r_{row['id']}")
                    if st.button("Confirmar", key=f"f_{row['id']}"):
                        supabase.table("monitorias").update({
                            "status_contestacao": decisao, "resposta_gestor": resp
                        }).eq("id", row['id']).execute()
                        st.rerun()