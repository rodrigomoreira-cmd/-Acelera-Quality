import streamlit as st
import pandas as pd
import time
# IMPORTANTE: Garante que estamos chamando a função nova do database.py
from database import get_criterios_ativos, salvar_monitoria_auditada, supabase

def render_nova_monitoria():
    st.title("📝 Nova Monitoria")
    st.markdown("Preencha o checklist abaixo. Lembre-se: **NC Grave zera a nota automaticamente.**")
    
    # 1. Busca os dados necessários (Critérios)
    df_criterios = get_criterios_ativos()
    
    # 2. Busca lista de SDRs ativos para o Selectbox
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
    # clear_on_submit=True garante que, após salvar com sucesso, os campos limpem
    with st.form("form_monitoria_dinamica", clear_on_submit=True):
        
        # BLOCO 1: IDENTIFICAÇÃO
        with st.container(border=True):
            st.markdown("### 👤 Identificação")
            col_sdr, col_link1, col_link2 = st.columns([2, 1.5, 1.5])
            
            sdr_escolhido = col_sdr.selectbox("Colaborador (SDR)", options=["Selecione..."] + lista_sdrs)
            link_selene = col_link1.text_input("Link da Conversa", placeholder="URL da gravação...")
            link_nectar = col_link2.text_input("Link do CRM", placeholder="URL do card...")

        st.markdown("<br>", unsafe_allow_html=True) 

        # BLOCO 2: AVALIAÇÃO (Checklist Dinâmico)
        respostas = {}
        grupos = df_criterios['grupo'].unique()
        
        for grupo in grupos:
            with st.expander(f"📂 {grupo}", expanded=True):
                itens = df_criterios[df_criterios['grupo'] == grupo]
                
                for _, row in itens.iterrows():
                    col_pergunta, col_resposta = st.columns([3, 2])
                    
                    nome_c = row['nome_criterio']
                    peso_c = float(row.get('peso', 1.0))
                    
                    col_pergunta.markdown(f"**{nome_c}**")
                    col_pergunta.caption(f"Peso: {peso_c}")
                    
                    # Criação dos Radio Buttons
                    respostas[nome_c] = {
                        "valor": col_resposta.radio(
                            f"Avaliação para {nome_c}", 
                            options=["C", "NC", "NC Grave", "NSA"],
                            index=0,
                            horizontal=True,
                            label_visibility="collapsed",
                            key=f"crit_{row['id']}"
                        ),
                        "peso": peso_c
                    }

        st.markdown("<br>", unsafe_allow_html=True)

        # BLOCO 3: CONCLUSÃO E FEEDBACK
        with st.container(border=True):
            st.markdown("### ✍️ Feedback Final")
            observacoes = st.text_area(
                "Observações Gerais:", 
                placeholder="Escreva aqui os pontos positivos e de melhoria. O SDR verá isso.",
                height=150
            )

        # BOTÃO DE ENVIO
        col_submit, _ = st.columns([1, 2])
        submitted = col_submit.form_submit_button("🚀 Finalizar Monitoria", use_container_width=True, type="primary")

        # --- LÓGICA DE PROCESSAMENTO ---
        if submitted:
            # 1. Validação de Campo Obrigatório
            if sdr_escolhido == "Selecione...":
                st.error("❌ Erro: Você deve selecionar um Colaborador (SDR).")
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
                
                # C = Soma tudo
                if resp == "C":
                    total_obtido += peso
                    total_possivel += peso
                # NC ou NC Grave = Soma só no possível (para reduzir a média)
                elif resp in ["NC", "NC Grave"]:
                    total_possivel += peso
                # NSA = Não soma em nada (neutro)

            # Regra: NC Grave zera a nota instantaneamente
            if tem_nc_grave:
                nota_final = 0.0
            else:
                nota_final = (total_obtido / total_possivel * 100) if total_possivel > 0 else 100.0

            # 3. Preparação dos Dados (Payload)
            payload = {
                "sdr": sdr_escolhido,
                "nota": round(nota_final, 2),
                "link_selene": link_selene,
                "link_nectar": link_nectar,
                "observacoes": observacoes,
                # Pega o nome do admin logado ou usa 'Admin' como fallback
                "monitor_responsavel": st.session_state.get('user_nome', 'Admin'),
                # Salva o dicionário de respostas detalhado
                "detalhes": {n: i["valor"] for n, i in respostas.items()}
            }

            # 4. Envio Seguro (Chama database.py)
            sucesso, msg = salvar_monitoria_auditada(payload)
            
            if sucesso:
                # Feedback Visual
                if tem_nc_grave:
                    st.error(f"🚨 NOTA ZERO APLICADA! Motivo: Falha Grave em '{', '.join(falhas_graves)}'")
                else:
                    # Define a cor do card baseada na nota
                    if nota_final >= 90: cor = "#00cc96" # Verde
                    elif nota_final >= 70: cor = "#ffa500" # Laranja
                    else: cor = "#ff4b4b" # Vermelho

                    st.markdown(f"""
                        <div style="background-color: {cor}20; border: 2px solid {cor}; padding: 20px; border-radius: 10px; text-align: center; margin-top: 20px;">
                            <h2 style="color: {cor}; margin:0;">Monitoria Registrada!</h2>
                            <h1 style="font-size: 50px; color: white; margin: 10px 0;">{nota_final:.1f}%</h1>
                            <p style="color: #ccc;">Monitor: {st.session_state.get('user_nome')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                    
                    # Opcional: Pausa breve para leitura antes de limpar (devido ao clear_on_submit)
                    time.sleep(3)
                    st.rerun()
            else:
                st.error(f"❌ Falha técnica ao salvar: {msg}")