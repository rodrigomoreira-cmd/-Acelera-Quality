import streamlit as st
import pandas as pd
from database import get_criterios_ativos, save_monitoria, supabase

def render_nova_monitoria():
    st.title("📝 Nova Monitoria de Qualidade")
    st.markdown("Avalie os itens conforme o checklist dinâmico. **NC Grave zera a nota final.**")
    
    # 1. Busca os critérios dinâmicos ativos no banco
    df_criterios = get_criterios_ativos()
    
    # 2. Busca lista de SDRs ativos para o Selectbox
    try:
        response = supabase.table("usuarios").select("nome").eq("nivel", "SDR").eq("esta_ativo", True).order("nome").execute()
        lista_sdrs = [u['nome'] for u in response.data] if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar lista de SDRs: {e}")
        lista_sdrs = []

    if df_criterios.empty:
        st.warning("⚠️ Nenhum critério ativo encontrado. Cadastre critérios em 'Config. Critérios' primeiro.")
        return

    with st.form("form_monitoria_dinamica", clear_on_submit=True):
        # --- CABEÇALHO ---
        col_sdr, col_vazio = st.columns([2, 2])
        sdr_escolhido = col_sdr.selectbox("Selecione o SDR", options=["Selecione..."] + lista_sdrs)
        
        st.markdown("##### 🔗 Links de Referência")
        c_link1, c_link2 = st.columns(2)
        link_selene = c_link1.text_input("Link SeleneBot", placeholder="https://web.whatsapp.com/...")
        link_nectar = c_link2.text_input("Link Néctar CRM", placeholder="https://app.nectarcrm.com.br/...")

        st.divider()
        
        # --- RENDERIZAÇÃO DINÂMICA DOS CRITÉRIOS POR GRUPO ---
        respostas = {}
        grupos = df_criterios['grupo'].unique()
        
        for grupo in grupos:
            with st.expander(f"📂 {grupo}", expanded=True):
                itens = df_criterios[df_criterios['grupo'] == grupo]
                
                for _, row in itens.iterrows():
                    nome_c = row['nome_criterio']
                    peso_c = float(row.get('peso', 1.0))
                    
                    # Interface de rádio para cada item
                    respostas[nome_c] = {
                        "valor": st.radio(
                            f"**{nome_c}** (Peso: {peso_c})",
                            options=["C", "NC", "NC Grave", "NSA"],
                            index=0, # Default em 'Conforme' para agilizar
                            horizontal=True,
                            key=f"crit_{row['id']}",
                            help="C: Conforme | NC: Não Conforme | NSA: Não se aplica"
                        ),
                        "peso": peso_c
                    }
        
        st.divider()
        observacoes = st.text_area("✍️ Feedback e Observações", placeholder="Pontos positivos, pontos a melhorar e orientações dadas ao SDR...")

        # --- PROCESSAMENTO DO CÁLCULO ---
        if st.form_submit_button("🚀 Finalizar e Salvar Monitoria", use_container_width=True, type="primary"):
            # Validações Iniciais
            if sdr_escolhido == "Selecione...":
                st.error("❌ Selecione o SDR antes de salvar.")
                st.stop()
            
            if not link_selene or not link_nectar:
                st.warning("⚠️ É recomendável preencher os links de referência para futuras consultas.")

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
                # NSA é ignorado no cálculo

            # Cálculo final da nota
            if tem_nc_grave:
                nota_final = 0.0
            else:
                nota_final = (total_obtido / total_possivel * 100) if total_possivel > 0 else 100.0

            # Montagem do Payload
            payload = {
                "sdr": sdr_escolhido,
                "nota": round(nota_final, 2),
                "link_selene": link_selene,
                "link_nectar": link_nectar,
                "observacoes": observacoes,
                "monitor_responsavel": st.session_state.get('user_nome', 'Admin'),
                "detalhes": {n: i["valor"] for n, i in respostas.items()} # JSON
            }

            try:
                save_monitoria(payload)
                
                if tem_nc_grave:
                    st.error(f"🚨 NOTA ZERO: Falha Grave em: {', '.join(falhas_graves)}")
                else:
                    st.success(f"✅ Monitoria salva! Nota Final: {nota_final:.1f}%")
                
                st.balloons()
                st.info("O SDR será notificado e a nota já está disponível no Dashboard.")
                
            except Exception as e:
                st.error(f"Erro técnico ao salvar: {e}")