import streamlit as st
from database import get_criterios_ativos, save_monitoria, supabase

def render_nova_monitoria():
    st.title("📝 Nova Monitoria de Qualidade")
    st.markdown("Avalie os itens conforme o checklist. Lembre-se: **NC Grave zera a nota final.**")
    
    # 1. Busca os critérios dinâmicos ativos
    df_criterios = get_criterios_ativos()
    
    # 2. Busca Usuários com tratamento de erro (Focado no Nome Completo)
    try:
        # Buscamos 'nome' e 'user' para garantir que salvamos o NOME COMPLETO como chave
        response = supabase.table("usuarios").select("nome, user, nivel").execute()
        todos_usuarios = response.data
        
        # Filtra apenas quem tem nível SDR (independente de maiúsculas/minúsculas)
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
        col1, col2 = st.columns(2)
        
        # --- SELEÇÃO DO SDR POR NOME COMPLETO ---
        if lista_sdrs_completa:
            # Opções começando com campo vazio para evitar salvamento acidental
            opcoes_nomes = ["Selecione o Nome do SDR..."] + sorted(lista_sdrs_completa)
            
            sdr_escolhido = col1.selectbox(
                "SDR Avaliado (Nome Completo)", 
                options=opcoes_nomes,
                index=0
            )
        else:
            st.info("💡 Nenhum SDR com nome cadastrado encontrado.")
            sdr_escolhido = col1.text_input("SDR Avaliado (Digite o Nome Completo)")

        # Monitor Responsável (Fixo pelo login da sessão)
        user_logado_login = st.session_state.get('user', 'admin')
        user_logado_nome = st.session_state.get('user_nome', 'Monitor')
        
        col2.text_input("Monitor Responsável", value=user_logado_nome, disabled=True)
        
        st.markdown("---")
        
        # --- RENDERIZAÇÃO DOS ITENS DE AVALIAÇÃO ---
        respostas = {}
        # Usa 'grupo' para organizar os itens na tela
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
            # Validação: Não permite salvar se não escolheu um SDR real
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
                # NSA não entra no cálculo (não soma no possível nem no obtido)

            # Regra de Negócio: NC Grave zera a nota automaticamente
            nota_final = 0.0 if tem_nc_grave else (total_obtido / total_possivel * 100 if total_possivel > 0 else 100)
            
            # Montagem do objeto para o banco de dados
            payload = {
                "sdr": sdr_escolhido, # Aqui salvamos o NOME COMPLETO (Ex: Ani Gabrielli)
                "nota": round(nota_final, 2),
                "observacoes": observacoes,
                "monitor_responsavel": user_logado_nome,
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