import streamlit as st
from database import supabase
from engine import CHECKLIST_MODEL, calculate_score_details

def render_monitoria():
    st.title("📝 Nova Monitoria de Qualidade")
    
    with st.form("form_monitoria"):
        col1, col2 = st.columns(2)
        sdr_nome = col1.text_input("Nome do SDR")
        data_ref = col2.date_input("Data da Monitoria")
        
        # Estado do checklist
        checklist_state = {}
        for item in CHECKLIST_MODEL:
            st.markdown(f"**{item['group']}**: {item['label']}")
            checklist_state[item['id']] = st.radio(
                "Avaliação", ["C", "NC", "NC Grave", "NSA"], 
                key=f"rad_{item['id']}", horizontal=True
            ).lower()
        
        obs = st.text_area("Observações Gerais")
        
        if st.form_submit_button("Salvar Monitoria"):
            results = calculate_score_details(CHECKLIST_MODEL, checklist_state)
            
            payload = {
                "sdr": sdr_nome,
                "data": str(data_ref),
                "nota": results['finalNota'],
                "observacoes": obs,
                "monitor_responsavel": st.session_state.user,
                "contestada": False, # Valor inicial
                "status_contestacao": "Nenhum"
            }
            
            try:
                supabase.table("monitorias").insert(payload).execute()
                st.success(f"Monitoria salva! Nota final: {results['finalNota']}%")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")