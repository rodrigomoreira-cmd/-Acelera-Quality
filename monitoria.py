import streamlit as st
from database import supabase
from engine import CHECKLIST_MODEL, calculate_score_details, THEME

def render_monitoria():
    # Estilização para as cores solicitadas
    st.markdown(f"""
        <style>
        h1, h2, h3 {{ color: {THEME['text']} !important; }}
        .stRadio > label {{ color: {THEME['text']} !important; }}
        </style>
    """, unsafe_allow_html=True)

    st.title("📝 Nova Monitoria de Qualidade")

    # 1. BUSCA DE SDRs CADASTRADOS
    try:
        res_usuarios = supabase.table("usuarios").select("nome").eq("nivel", "sdr").execute()
        # Adicionamos uma opção em branco no início da lista
        lista_sdrs = [""] + [user['nome'] for user in res_usuarios.data] if res_usuarios.data else [""]
    except Exception as e:
        st.error(f"Erro ao carregar lista de SDRs: {e}")
        lista_sdrs = [""]

    if len(lista_sdrs) <= 1:
        st.warning("⚠️ Nenhum SDR cadastrado encontrado. Cadastre um SDR na tela de Cadastro primeiro.")
        return

    # 2. FORMULÁRIO DE MONITORIA
    with st.form("form_monitoria"):
        col1, col2 = st.columns(2)
        
        # O index=0 aponta para o campo vazio ("")
        sdr_selecionado = col1.selectbox(
            "Selecione o SDR", 
            options=lista_sdrs, 
            index=0,
            format_func=lambda x: "Selecione um nome..." if x == "" else x
        )
        
        data_ref = col2.date_input("Data da Monitoria")
        
        st.divider()
        
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
            # VALIDAÇÃO: Impede salvar se o SDR estiver em branco
            if sdr_selecionado == "":
                st.error("❌ Erro: Você precisa selecionar um SDR antes de salvar!")
            else:
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
                    st.success(f"✅ Monitoria de {sdr_selecionado} salva com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")