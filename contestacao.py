import streamlit as st
import pandas as pd
from database import supabase, get_all_records_db

def render_contestacao():
    st.title("⚖️ Minhas Monitorias e Contestações")
    
    # 1. BUSCA DADOS
    df = get_all_records_db("monitorias")
    
    if df.empty:
        st.info("Você ainda não possui monitorias registradas.")
        return

    # 2. FILTRO: SDR só vê as suas
    # Administrador vê todas (opcional, conforme seu pedido de histórico visível para admin)
    if st.session_state.get('nivel') == 'sdr':
        df = df[df['sdr'] == st.session_state.user]

    # Exibe as monitorias em formato de cards ou lista para seleção
    st.subheader("Selecione uma monitoria para revisar ou contestar")
    
    for index, row in df.iterrows():
        # Layout de cada registro
        with st.expander(f"📅 {row['data']} - Nota: {row['nota']}% - SDR: {row['sdr']}"):
            st.write(f"**Observações do Monitor:** {row['observacoes']}")
            
            # Verifica se já foi contestada
            if row.get('contestada'):
                st.warning(f"⚠️ **Monitoria Contestada:** {row['motivo_contestacao']}")
            else:
                # O botão de contestação abre um "popover" (que funciona como um popup moderno)
                with st.popover("CONTESTAR"):
                    st.write("Deseja realmente contestar esta nota?")
                    col_sim, col_nao = st.columns(2)
                    
                    if col_sim.button("SIM", key=f"sim_{row['id']}", use_container_width=True):
                        st.session_state[f"edit_{row['id']}"] = True
                    
                    if col_nao.button("NÃO", key=f"nao_{row['id']}", use_container_width=True):
                        st.rerun()

                    # Se clicou em SIM, abre o campo de texto
                    if st.session_state.get(f"edit_{row['id']}"):
                        motivo = st.text_area("Descreva o motivo da contestação:", key=f"text_{row['id']}")
                        if st.button("Enviar Contestação", key=f"env_{row['id']}"):
                            if motivo:
                                try:
                                    supabase.table("monitorias").update({
                                        "contestada": True,
                                        "motivo_contestacao": motivo
                                    }).eq("id", row['id']).execute()
                                    
                                    st.success("Contestação enviada!")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")
                            else:
                                st.warning("Por favor, escreva o motivo.")