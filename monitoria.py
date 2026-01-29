import streamlit as st
from database import get_criterios_ativos, save_monitoria, supabase

def render_nova_monitoria():
    st.title("📝 Nova Monitoria de Qualidade")
    st.markdown("Avalie os itens conforme o checklist. Lembre-se: **NC Grave zera a nota final.**")
    
    # 1. Busca os critérios dinâmicos ativos
    df_criterios = get_criterios_ativos()
    
    # 2. Busca Usuários com tratamento de erro
    try:
        response = supabase.table("usuarios").select("nome, user, nivel").execute()
        todos_usuarios = response.data
        
        lista_sdrs_completa = [
            u['nome'] for u in todos_usuarios 
            if str(u.get('nivel', '')).strip().upper() == "SDR" and u.get('nome')
        ]
    except Exception as e:
        st.error(f"Erro ao carregar lista de SDRs: {e}")
        lista_sdrs_completa = []

    if df_criterios.empty:
        st.warning("⚠️ Cadastre critérios em 'Config. Critérios' primeiro.")
        return

    with st.form("form_monitoria_v5"):
        # --- PRIMEIRA LINHA: SDR E MONITOR ---
        col1, col2 = st.columns(2)
        
        if lista_sdrs_completa:
            opcoes_nomes = ["Selecione o Nome do SDR..."] + sorted(lista_sdrs_completa)
            sdr_escolhido = col1.selectbox(
                "SDR Avaliado (Nome Completo)", 
                options=opcoes_nomes,
                index=0
            )
        else:
            sdr_escolhido = col1.text_input("SDR Avaliado (Digite o Nome Completo)")

        user_logado_nome = st.session_state.get('user_nome', 'Monitor')
        col2.text_input("Monitor Responsável", value=user_logado_nome, disabled=True)
        
        # --- SEGUNDA LINHA: LINKS EXTERNOS (SELENE E NÉCTAR) ---
        st.markdown("##### 🔗 Links de Referência")
        col_link1, col_link2 = st.columns(2)
        link_selene = col_link1.text_input("Link SeleneBot", placeholder="https://selenebot.com/...")
        link_nectar = col_link2.text_input("Link Néctar CRM", placeholder="https://app.nectarcrm.com.br/...")

        st.markdown("---")
        
        # --- RENDERIZAÇÃO DOS ITENS DE AVALIAÇÃO ---
        respostas = {}
        coluna_grupo = 'grupo' if 'grupo' in df_criterios.columns else 'id'
        df_criterios = df_criterios.sort_values(by=[coluna_grupo, 'id'])
        
        for grupo, itens in df_criterios.groupby(coluna_grupo, sort=False):
            st.subheader(f"📂 {grupo}")
            for _, row in itens.iterrows():
                nome_c = row['nome_criterio']
                peso_c = row.get('peso', 1)
                
                respostas[nome_c] = {
                    "valor": st.radio(
                        f"**{nome_c}** (Peso: {peso_c})", 
                        ["C", "NC", "NC Grave", "NSA"], 
                        horizontal=True, 
                        key=f"mon_crit_{row['id']}"
                    ),
                    "peso": peso_c
                }

        st.markdown("---")
        observacoes = st.text_area("✍️ Feedback para o SDR (Aparecerá no portal dele)")

        # --- PROCESSAMENTO DO FORMULÁRIO ---
        btn_salvar = st.form_submit_button("Finalizar Monitoria")

        if btn_salvar:
            if sdr_escolhido == "Selecione o Nome do SDR..." or not sdr_escolhido:
                st.error("❌ Erro: Selecione o nome do SDR antes de salvar.")
                st.stop()

            # Cálculo Matemático da Nota
            total_possivel = 0
            total_obtido = 0
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

            nota_final = 0.0 if tem_nc_grave else (total_obtido / total_possivel * 100 if total_possivel > 0 else 100)
            
            # Montagem do objeto para o banco de dados (Payload atualizado com links)
            payload = {
                "sdr": sdr_escolhido,
                "nota": round(nota_final, 2),
                "observacoes": observacoes,
                "monitor_responsavel": user_logado_nome,
                "link_selene": link_selene,
                "link_nectar": link_nectar,
                "detalhes": {n: i["valor"] for n, i in respostas.items()}
            }
            
            try:
                save_monitoria(payload)
                
                if tem_nc_grave:
                    st.error(f"🚨 Nota Zero aplicada devido a NC Grave em: {', '.join(falhas_graves)}")
                else:
                    st.success(f"✅ Monitoria de {sdr_escolhido} salva com sucesso! Nota: {nota_final:.2f}%")
                
                st.balloons()
                
            except Exception as e:
                st.error(f"Erro técnico ao salvar no banco: {e}")