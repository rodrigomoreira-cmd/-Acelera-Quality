import streamlit as st
from database import supabase
from engine import CHECKLIST_MODEL, calculate_score_details

def render_monitoria():
    st.title("📝 Nova Monitoria de Qualidade")

    # 1. BUSCA DE SDRs CADASTRADOS
    try:
        # Busca apenas usuários com nível 'sdr'
        res_usuarios = supabase.table("usuarios").select("nome").eq("nivel", "sdr").execute()
        lista_sdrs = [user['nome'] for user in res_usuarios.data] if res_usuarios.data else []
    except Exception as e:
        st.error(f"Erro ao carregar lista de SDRs: {e}")
        lista_sdrs = []

    if not lista_sdrs:
        st.warning("⚠️ Nenhum SDR cadastrado encontrado. Cadastre um SDR na tela de Cadastro primeiro.")
        return

    # 2. FORMULÁRIO DE MONITORIA
    with st.form("form_monitoria"):
        col1, col2 = st.columns(2)
        
        # Agora o campo é um Selectbox com os nomes vindos do banco
        sdr_selecionado = col1.selectbox("Selecione o SDR", options=lista_sdrs)
        data_ref = col2.date_input("Data da Monitoria")
        
        st.divider()
        
        # Estado do checklist
        checklist_state = {}
        for item in CHECKLIST_MODEL:
            st.markdown(f"**{item['group']}**: {item['label']}")
            checklist_state[item['id']] = st.radio(
                "Avaliação", ["C", "NC", "NC Grave", "NSA"], 
                key=f"rad_{item['id']}", horizontal=True
            ).lower()
        
        st.divider()
        obs = st.text_area("Observações Gerais / Feedbacks")
        
        if st.form_submit_button("Salvar Monitoria"):
            # Calcula a nota usando a lógica do engine.py
            results = calculate_score_details(CHECKLIST_MODEL, checklist_state)
            
            payload = {
                "sdr": sdr_selecionado,
                "data": str(data_ref),
                "nota": results['finalNota'],
                "observacoes": obs,
                "monitor_responsavel": st.session_state.user,
                "contestada": False,
                "status_contestacao": "Nenhum"
            }
            
            try:
                supabase.table("monitorias").insert(payload).execute()
                st.success(f"✅ Monitoria de {sdr_selecionado} salva! Nota: {results['finalNota']}%")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar no banco: {e}")