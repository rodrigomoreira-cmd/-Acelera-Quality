import streamlit as st
import pandas as pd
from database import supabase, get_all_records_db

def render_contestacao():
    st.title("⚖️ Minhas Monitorias e Contestações")
    
    # Busca dados gerais do banco
    df = get_all_records_db("monitorias")
    
    if df.empty:
        st.info("Você ainda não possui monitorias registradas.")
        return

    # Filtro: SDR logado vê apenas as suas monitorias
    if st.session_state.get('nivel') == 'sdr':
        df = df[df['sdr'] == st.session_state.user]

    st.subheader("Selecione uma monitoria para revisar ou contestar")
    
    for index, row in df.iterrows():
        # Expander para detalhar a monitoria
        with st.expander(f"📅 {row['data']} - Nota: {row['nota']}% - SDR: {row['sdr']}"):
            st.write(f"**Observações do Monitor:** {row['observacoes']}")
            
            # Verifica se já foi contestada
            if row.get('contestada'):
                st.warning(f"⚠️ **Contestada:** {row['motivo_contestacao']}")
            else:
                # Popover para ação de contestar
                with st.popover("CONTESTAR"):
                    st.write("Deseja contestar esta nota?")
                    col_sim, col_nao = st.columns(2)
                    
                    if col_sim.button("SIM", key=f"sim_{row['id']}", use_container_width=True):
                        st.session_state[f"edit_{row['id']}"] = True
                    
                    if col_nao.button("NÃO", key=f"nao_{row['id']}", use_container_width=True):
                        st.rerun()

                    # Campo para o motivo caso clique em SIM
                    if st.session_state.get(f"edit_{row['id']}"):
                        motivo = st.text_area("Motivo da contestação:", key=f"text_{row['id']}")
                        if st.button("Enviar", key=f"env_{row['id']}"):
                            if motivo:
                                try:
                                    supabase.table("monitorias").update({
                                        "contestada": True,
                                        "motivo_contestacao": motivo
                                    }).eq("id", row['id']).execute()
                                    st.success("Enviada!")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")