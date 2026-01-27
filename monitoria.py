# monitoria.py
import streamlit as st
from engine import CHECKLIST_MODEL, calculate_score_details
from database import supabase, get_sdr_names_db
from datetime import datetime

def render_monitoria():
    st.title("📝 Monitoria de Qualidade")
    
    nomes_sdr = get_sdr_names_db()
    
    with st.form("form_monitoria"):
        # Dados Básicos
        col1, col2 = st.columns(2)
        sdr = col1.selectbox("SDR", [""] + nomes_sdr)
        crm_link = col2.text_input("Link Nectar CRM")
        selene_link = st.text_input("Link Selene")
        
        st.divider()
        
        # Gerar Checklist dinamicamente por Grupos
        respostas = {}
        grupos = sorted(list(set(item['group'] for item in CHECKLIST_MODEL)))
        
        for grupo in grupos:
            st.subheader(f"📂 {grupo}")
            itens_grupo = [i for i in CHECKLIST_MODEL if i['group'] == grupo]
            
            for item in itens_grupo:
                respostas[item['id']] = st.radio(
                    label=item['label'],
                    options=["conforme", "nc", "nc_grave", "nsa"],
                    index=0,
                    horizontal=True,
                    key=item['id']
                )
            st.divider()

        observacoes = st.text_area("Observações")
        plano_acao = st.text_area("Plano de Ação")
        
        if st.form_submit_button("Finalizar e Salvar"):
            if not sdr:
                st.error("Selecione um SDR.")
                return

            # Cálculo usando o engine
            score_details = calculate_score_details(CHECKLIST_MODEL, respostas)
            
            payload = {
                "sdr": sdr,
                "data": datetime.now().strftime('%Y-%m-%d'),
                "hora": datetime.now().strftime('%H:%M:%S'),
                "crm_link": crm_link,
                "selene_link": selene_link,
                "nota": score_details['finalNota'],
                "observacoes": observacoes,
                "plano_acao": plano_acao,
                "checklist_json": respostas
            }
            
            try:
                supabase.table("monitorias").insert(payload).execute()
                st.success(f"Salvo! Nota Final: {payload['nota']}%")
                st.balloons()
            except Exception as e:
                st.error(f"Erro: {e}")