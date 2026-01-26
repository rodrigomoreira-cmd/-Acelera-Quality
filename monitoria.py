import streamlit as st
from datetime import datetime
from database import supabase, get_sdr_names_db  # Importa conexão e busca de nomes
from engine import calculate_score_details       # Importa a lógica de cálculo

def render_monitoria():
    st.title("📝 Nova Monitoria de Qualidade")

    # Inicializa o formulário no session_state se não existir
    if 'monitoria_form' not in st.session_state:
        st.session_state.monitoria_form = {
            'sdr': '', 
            'crmLink': '', 
            'seleneLink': '', 
            'checklist': {}, 
            'observacoes': '', 
            'planoAcaoMonitor': ''
        }

    # Busca a lista de SDRs do Supabase (Modularizado no database.py)
    nomes_sdr = get_sdr_names_db()

    with st.form("form_registro_monitoria"):
        col1, col2 = st.columns(2)
        
        # Seleção do SDR
        st.session_state.monitoria_form['sdr'] = col1.selectbox(
            "Selecione o SDR Monitorado", 
            options=[""] + nomes_sdr
        )
        
        st.session_state.monitoria_form['crmLink'] = col2.text_input(
            "Link do CRM (Lead)", 
            value=st.session_state.monitoria_form['crmLink']
        )
        
        st.session_state.monitoria_form['seleneLink'] = st.text_input(
            "Link do Selene/Chat", 
            value=st.session_state.monitoria_form['seleneLink']
        )
        
        st.divider()
        st.subheader("Checklist de Avaliação")

        # Exemplo de Blocos de Perguntas (Você pode carregar estes itens do banco no futuro)
        # Bloco: Processo
        st.markdown("**Processo e Atendimento**")
        c1 = st.radio("O lead foi atendido em menos de 15min?", ["conforme", "nc", "nc_grave"], horizontal=True, key="q1")
        c2 = st.radio("As etapas do funil estão atualizadas no CRM?", ["conforme", "nc", "nc_grave"], horizontal=True, key="q2")
        
        # Mapeia as respostas para o dicionário de checklist
        st.session_state.monitoria_form['checklist'] = {
            "atendimento_15m": c1,
            "funil_crm": c2
        }

        st.divider()
        st.session_state.monitoria_form['observacoes'] = st.text_area("Observações Gerais")
        st.session_state.monitoria_form['planoAcaoMonitor'] = st.text_area("Plano de Ação para o SDR")

        # BOTÃO DE SALVAMENTO
        if st.form_submit_button("SALVAR MONITORIA NO SUPABASE"):
            if not st.session_state.monitoria_form['sdr']:
                st.error("Por favor, selecione um SDR antes de salvar.")
            else:
                # 1. Define o modelo de pesos (IDs devem bater com o checklist acima)
                checklist_model = [
                    {"id": "atendimento_15m", "weight": 50, "group": "Selene"},
                    {"id": "funil_crm", "weight": 50, "group": "CRM"}
                ]

                # 2. Executa o cálculo usando o módulo engine.py
                score_details = calculate_score_details(checklist_model, st.session_state.monitoria_form['checklist'])

                # 3. Prepara o payload para o Supabase
                payload = {
                    "sdr": st.session_state.monitoria_form['sdr'],
                    "data": datetime.now().strftime('%Y-%m-%d'),
                    "hora": datetime.now().strftime('%H:%M:%S'),
                    "crm_link": st.session_state.monitoria_form['crmLink'],
                    "selene_link": st.session_state.monitoria_form['seleneLink'],
                    "nota": score_details['finalNota'],
                    "observacoes": st.session_state.monitoria_form['observacoes'],
                    "plano_acao": st.session_state.monitoria_form['planoAcaoMonitor'],
                    "checklist_json": st.session_state.monitoria_form['checklist']
                }

                # 4. Envia para o Banco de Dados
                try:
                    supabase.table("monitorias").insert(payload).execute()
                    st.success(f"✅ Monitoria de {payload['sdr']} salva com sucesso!")
                    st.balloons()
                    # Limpa o formulário
                    st.session_state.monitoria_form = {
                        'sdr': '', 'crmLink': '', 'seleneLink': '', 
                        'checklist': {}, 'observacoes': '', 'planoAcaoMonitor': ''
                    }
                except Exception as e:
                    st.error(f"Erro ao salvar no banco de dados: {e}")