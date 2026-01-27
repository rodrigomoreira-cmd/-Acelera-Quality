import streamlit as st
from database import supabase, get_all_records_db

def render_contestacao():
    nivel = st.session_state.get('nivel', 'sdr').upper()
    st.title("⚖️ Central de Contestações")
    
    df = get_all_records_db("monitorias")
    if df.empty:
        st.info("Nenhuma monitoria disponível.")
        return

    # Filtros de visualização
    if nivel == 'SDR':
        # SDR vê apenas suas monitorias
        df_view = df[df['sdr'] == st.session_state.user]
    else:
        # ADMIN vê apenas as que possuem contestação ativa para responder
        df_view = df[df['contestada'] == True]

    st.write(f"Exibindo registros para: **{nivel}**")

    for index, row in df_view.iterrows():
        status = row.get('status_contestacao', 'Pendente')
        # Emoji dinâmico baseado no status
        emoji = "🟠" if status == "Pendente" else "🟢" if status == "Deferido" else "🔴"
        
        with st.expander(f"{emoji} Monitoria: {row['data']} | Nota: {row['nota']}%"):
            st.write(f"**Observações do Monitor:** {row['observacoes']}")
            
            # --- ÁREA DO SDR (PARA CONTESTAR) ---
            if nivel == "SDR":
                if row.get('contestada'):
                    st.warning(f"**Sua contestação:** {row['motivo_contestacao']}")
                    if row.get('resposta_gestor'):
                        st.info(f"**Resposta do Gestor:** {row['resposta_gestor']}")
                else:
                    with st.popover("CONTESTAR ESTA NOTA"):
                        motivo = st.text_area("Explique por que você discorda da nota:", key=f"mot_{row['id']}")
                        if st.button("Enviar Contestação", key=f"btn_{row['id']}"):
                            if motivo:
                                supabase.table("monitorias").update({
                                    "contestada": True, 
                                    "motivo_contestacao": motivo,
                                    "status_contestacao": "Pendente"
                                }).eq("id", row['id']).execute()
                                st.success("Contestação enviada!")
                                st.rerun()

            # --- ÁREA DO ADMIN (PARA RESPONDER) ---
            else:
                st.markdown("---")
                st.write(f"**Argumento do SDR:** {row['motivo_contestacao']}")
                
                with st.popover("RESPONDER CONTESTAÇÃO"):
                    decisao = st.selectbox("Decisão", ["Deferido", "Indeferido"], key=f"dec_{row['id']}")
                    justificativa = st.text_area("Resposta ao SDR:", key=f"res_{row['id']}")
                    if st.button("Finalizar Revisão", key=f"fina_{row['id']}"):
                        supabase.table("monitorias").update({
                            "resposta_gestor": justificativa,
                            "status_contestacao": decisao
                        }).eq("id", row['id']).execute()
                        st.success("Resposta enviada com sucesso!")
                        st.rerun()