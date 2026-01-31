import streamlit as st
import pandas as pd
from database import get_criterios_ativos, save_monitoria, supabase

def render_nova_monitoria():
    st.title("📝 Nova Monitoria")
    st.markdown("Preencha o checklist abaixo. Lembre-se: **NC Grave zera a nota automaticamente.**")
    
    # 1. Busca os dados necessários
    df_criterios = get_criterios_ativos()
    
    # Busca lista de SDRs
    try:
        response = supabase.table("usuarios").select("nome").eq("nivel", "SDR").eq("esta_ativo", True).order("nome").execute()
        lista_sdrs = [u['nome'] for u in response.data] if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar lista de SDRs: {e}")
        lista_sdrs = []

    if df_criterios.empty:
        st.warning("⚠️ Nenhum critério ativo. Vá em 'Config. Critérios' para cadastrar.")
        return

    # --- INÍCIO DO FORMULÁRIO ---
    with st.form("form_monitoria_dinamica", clear_on_submit=True):
        
        # BLOC 1: IDENTIFICAÇÃO (Em um container para destaque)
        with st.container(border=True):
            st.markdown("### 👤 Identificação")
            col_sdr, col_link1, col_link2 = st.columns([2, 1.5, 1.5])
            
            sdr_escolhido = col_sdr.selectbox("Colaborador (SDR)", options=["Selecione..."] + lista_sdrs)
            link_selene = col_link1.text_input("Link da Conversa", placeholder="URL...")
            link_nectar = col_link2.text_input("Link do CRM", placeholder="URL...")

        st.markdown("<br>", unsafe_allow_html=True) # Espaço visual

        # BLOCO 2: AVALIAÇÃO (Checklist)
        respostas = {}
        grupos = df_criterios['grupo'].unique()
        
        for grupo in grupos:
            # Expander aberto por padrão para facilitar a leitura rápida
            with st.expander(f"📂 {grupo}", expanded=True):
                itens = df_criterios[df_criterios['grupo'] == grupo]
                
                for _, row in itens.iterrows():
                    col_pergunta, col_resposta = st.columns([3, 2])
                    
                    nome_c = row['nome_criterio']
                    peso_c = float(row.get('peso', 1.0))
                    
                    col_pergunta.markdown(f"**{nome_c}**")
                    col_pergunta.caption(f"Peso: {peso_c}")
                    
                    # Rádio horizontal para agilidade
                    respostas[nome_c] = {
                        "valor": col_resposta.radio(
                            f"Avaliação para {nome_c}", # Label invisível (hidden) por acessibilidade
                            options=["C", "NC", "NC Grave", "NSA"],
                            index=0,
                            horizontal=True,
                            label_visibility="collapsed",
                            key=f"crit_{row['id']}"
                        ),
                        "peso": peso_c
                    }

        st.markdown("<br>", unsafe_allow_html=True)

        # BLOCO 3: CONCLUSÃO
        with st.container(border=True):
            st.markdown("### ✍️ Feedback Final")
            observacoes = st.text_area(
                "Escreva os pontos positivos e de melhoria:", 
                placeholder="Este feedback aparecerá para o SDR na tela de 'Meus Resultados'...",
                height=150
            )

        # BOTÃO DE AÇÃO
        col_submit, _ = st.columns([1, 2])
        submitted = col_submit.form_submit_button("🚀 Finalizar Monitoria", use_container_width=True, type="primary")

        # --- LÓGICA DE SALVAMENTO ---
        if submitted:
            # 1. Validação Básica
            if sdr_escolhido == "Selecione...":
                st.error("❌ Por favor, selecione um SDR.")
                st.stop()
            
            # 2. Cálculo da Nota
            total_possivel = 0.0
            total_obtido = 0.0
            tem_nc_grave = False
            falhas_graves = []

            for nome, item in respostas.items():
                resp = item["valor"]
                peso = item["peso"]

                if resp == "NC Grave":
                    tem_nc_grave = True
                    falhas_graves.append(nome)
                
                if resp == "C":
                    total_obtido += peso
                    total_possivel += peso
                elif resp in ["NC", "NC Grave"]:
                    total_possivel += peso
                # NSA não soma no 'total_possivel', então não penaliza a média

            # Regra de Ouro: NC Grave zera tudo
            if tem_nc_grave:
                nota_final = 0.0
            else:
                nota_final = (total_obtido / total_possivel * 100) if total_possivel > 0 else 100.0

            # 3. Prepara o Payload para o Banco
            payload = {
                "sdr": sdr_escolhido,
                "nota": round(nota_final, 2),
                "link_selene": link_selene,
                "link_nectar": link_nectar,
                "observacoes": observacoes,
                "monitor_responsavel": st.session_state.get('user_nome', 'Admin'),
                "detalhes": {n: i["valor"] for n, i in respostas.items()} # Salva o JSON das respostas
            }

            try:
                save_monitoria(payload)
                
                # 4. Feedback Visual de Sucesso
                if tem_nc_grave:
                    st.error(f"🚨 NOTA ZERO APLICADA! Falha Grave em: {', '.join(falhas_graves)}")
                else:
                    cor_nota = "#00cc96" if nota_final >= 90 else "#ffa500" if nota_final >= 70 else "#ff4b4b"
                    st.markdown(f"""
                        <div style="background-color: {cor_nota}20; border: 2px solid {cor_nota}; padding: 20px; border-radius: 10px; text-align: center; margin-top: 20px;">
                            <h2 style="color: {cor_nota}; margin:0;">Monitoria Salva com Sucesso!</h2>
                            <h1 style="font-size: 50px; color: white; margin: 10px 0;">{nota_final:.1f}%</h1>
                            <p style="color: #ccc;">O SDR {sdr_escolhido} já pode visualizar este resultado.</p>
                        </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                
            except Exception as e:
                st.error(f"Erro técnico ao salvar: {e}")