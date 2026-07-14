import streamlit as st
import pandas as pd
from datetime import datetime
import time

# Importações do seu banco de dados
from database import supabase, get_all_records_db, registrar_auditoria

# ==========================================================
# 📋 CRITÉRIOS DE BACKUP (Caso a internet falhe ou banco esteja vazio)
# ==========================================================
CRITERIOS_N1_BACKUP = [
    "Não realizar o primeiro contato através do Selene Bot quando aplicável.",
    "Utilizar canal de contato diferente do recomendado para a origem do lead.",
    "Registrar motivo de descarte sem detalhamento adequado.",
    "Deixar de confirmar formalmente o envio do convite e link da reunião.",
    "Não utilizar canais alternativos de contato quando recomendados pelo processo.",
    "Deixar pendências operacionais de baixo impacto na gestão do card."
]

CRITERIOS_N2_BACKUP = [
    "Não registrar adequadamente informações do ICP.",
    "Avançar lead sem validação completa dos critérios obrigatórios.",
    "Movimentar o card para qualificação sem evidências suficientes de ICP e interesse.",
    "Conduzir atendimento sem abordagem consultiva mínima.",
    "Não alinhar expectativas da reunião com o lead.",
    "Realizar descarte sem justificativa adequada.",
    "Não transferir informações relevantes para preparação do Especialista.",
    "Falhas de preenchimento relevantes que prejudiquem a continuidade do processo."
]

CRITERIOS_N3_BACKUP = [
    "Não iniciar contato com o lead dentro do prazo operacional definido sem justificativa válida.",
    "Deixar lead parado na etapa 'Novos Leads' por período superior ao permitido.",
    "Realizar descarte fora da etapa correta do processo.",
    "Não executar a cadência mínima obrigatória antes de encerrar a tentativa de contato.",
    "Deixar lead sem interação por período superior ao permitido durante atendimento ativo.",
    "Realizar contatos sem registro adequado nos sistemas oficiais da empresa.",
    "Avançar lead sem validação mínima de ICP.",
    "Forçar avanço de lead sem aderência ao perfil definido pela empresa.",
    "Agendar reunião sem preenchimento completo do formulário oficial de qualificação.",
    "Realizar distribuição indevida de agenda ou descumprir regras de Round Robin.",
    "Não executar o processo obrigatório de reagendamento após No Show.",
    "Manter status incorreto do lead no CRM gerando distorção dos indicadores.",
    "Manipular informações comerciais, registros ou métricas.",
    "Utilizar ferramentas, formulários, processos ou metodologias diferentes das oficialmente definidas.",
    "Deixar de utilizar sistemas obrigatórios para registro e acompanhamento das atividades."
]

# ==========================================================
# 🔄 FUNÇÃO PARA BUSCAR CRITÉRIOS DO BANCO (criterios_qa)
# ==========================================================
def buscar_criterios_dinamicos():
    """Busca as perguntas baseadas na estrutura exata do seu Supabase, sem cache para atualização em tempo real."""
    try:
        df_crit = get_all_records_db("criterios_qa")
        if df_crit is not None and not df_crit.empty:
            
            n1, n2, n3 = [], [], []
            
            for _, row in df_crit.iterrows():
                # 1. Verifica se está ativo de forma robusta (aceita booleano True ou texto 'true')
                ativo = str(row.get("esta_ativo", "True")).strip().lower()
                if ativo not in ['true', '1', 't', 'yes', 'sim']:
                    continue # Se estiver desativado, pula!
                    
                # 2. Pega o texto (compara 'nome' e 'descricao' e usa o mais longo)
                texto_nome = str(row.get("nome", "")).strip()
                texto_desc = str(row.get("descricao", "")).strip()
                
                texto_final = texto_desc if len(texto_desc) > len(texto_nome) else texto_nome
                    
                if not texto_final or texto_final.lower() == "nan":
                    continue
                    
                # 3. Lê grupo e peso
                grupo = str(row.get("grupo", "")).strip().upper()
                
                try:
                    peso_val = float(row.get("peso", 0)) # Transforma em número real para evitar erros de texto
                except:
                    peso_val = 0
                
                # 4. Distribui o critério pela aba correta
                if "N1" in grupo or peso_val == 1:
                    n1.append(texto_final)
                elif "N2" in grupo or peso_val == 3:
                    n2.append(texto_final)
                elif "N3" in grupo or peso_val == 7:
                    n3.append(texto_final)
                    
            # Se conseguiu carregar pelo menos uma pergunta, retorna as listas oficiais!
            if n1 or n2 or n3:
                return n1, n2, n3
                
    except Exception as e:
        print(f"Erro ao ler os critérios do banco: {e}")
        
    # Se algo falhar gravemente, avisa no terminal e usa o Backup
    print("Usando critérios de backup!")
    return CRITERIOS_N1_BACKUP, CRITERIOS_N2_BACKUP, CRITERIOS_N3_BACKUP

# ==========================================================
# 🖥️ RENDERIZAÇÃO DA TELA DE MONITORIA
# ==========================================================
def render_nova_monitoria():
    st.markdown("<h1 style='color: #FF7A00;'>📝 Nova Monitoria de Qualidade</h1>", unsafe_allow_html=True)
    st.write("Avalie o atendimento aplicando as penalidades N1, N2 e N3. A nota parte de 100%.")
    st.write("---")

    auditor_nome = st.session_state.get("user_nome", "Auditor Desconhecido")

    # ==========================================================
    # 🔍 BUSCA INTELIGENTE DE SDRs NO BANCO DE DADOS
    # ==========================================================
    df_usuarios = get_all_records_db("usuarios")
    lista_sdrs = []
    
    if df_usuarios is not None and not df_usuarios.empty:
        if 'departamento' in df_usuarios.columns:
            df_filtrado = df_usuarios[df_usuarios['departamento'].astype(str).str.upper() == 'SDR']
            lista_sdrs = df_filtrado['nome'].dropna().unique().tolist()
        elif 'nivel' in df_usuarios.columns:
            df_filtrado = df_usuarios[df_usuarios['nivel'].astype(str).str.upper() == 'SDR']
            lista_sdrs = df_filtrado['nome'].dropna().unique().tolist()
        else:
            lista_sdrs = df_usuarios['nome'].dropna().unique().tolist()
            
    lista_sdrs = sorted(lista_sdrs) if lista_sdrs else ["Nenhum usuário encontrado"]

    # 1. DADOS PRINCIPAIS DA AVALIAÇÃO
    with st.container(border=True):
        st.markdown("### 👤 Dados do Avaliado")
        col1, col2 = st.columns(2)
        
        # Adicionado chaves (keys) aos widgets para possibilitar a limpeza remota
        sdr_selecionado = col1.selectbox("Selecione o SDR:", [""] + lista_sdrs, key="sdr_selecionado_widget")
        data_avaliacao = col2.date_input("Data da Avaliação:", datetime.today(), key="data_avaliacao_widget")
        
        col_link1, col_link2 = st.columns(2)
        link_selene = col_link1.text_input("🔗 Link do Selene (Gravação):", placeholder="https://...", key="link_selene_widget")
        link_nectar = col_link2.text_input("🗂️ Link do Nectar (Card):", placeholder="https://...", key="link_nectar_widget")

    st.write("##")
    
    # ==========================================================
    # 🛑 REGRA MÁGICA: SÓ CARREGA SE O SDR ESTIVER SELECIONADO
    # ==========================================================
    if not sdr_selecionado or sdr_selecionado == "Nenhum usuário encontrado":
        st.info("👈 Por favor, selecione um SDR no campo acima para carregar o formulário de avaliação.")
        return 
    
    # Busca os critérios do banco
    criterios_n1, criterios_n2, criterios_n3 = buscar_criterios_dinamicos()
    
    # 2. SISTEMA DE ABAS (N1, N2, N3)
    tab_n1, tab_n2, tab_n3 = st.tabs(["🟢 N1 (Penalidade: -1%)", "🟡 N2 (Penalidade: -3%)", "🔴 N3 (Penalidade: -7%)"])
    
    respostas_monitoria = {}

    def render_perguntas(lista_perguntas, peso_penalidade, tab_context):
        """Função auxiliar para renderizar as perguntas em caixas abertas"""
        penalidade_acumulada = 0
        with tab_context:
            if not lista_perguntas:
                st.info("Nenhum critério ativo cadastrado para este nível.")
                
            for pergunta in lista_perguntas:
                with st.container(border=True):
                    st.markdown(f"**📌 {pergunta}**")
                    
                    status = st.radio(
                        "Avaliação:",
                        options=["C", "NC", "NSA"],
                        index=0, 
                        key=f"radio_{pergunta}",
                        horizontal=True,
                        format_func=lambda x: "✅ Conforme" if x == "C" else "❌ Não Conforme" if x == "NC" else "➖ Não Se Aplica (NSA)",
                        label_visibility="collapsed"
                    )
                    
                    comentario = ""
                    if status == "NC":
                        st.warning(f"⚠️ Penalidade de -{peso_penalidade}% será aplicada.")
                        comentario = st.text_area("Motivo da Não Conformidade (Obrigatório):", key=f"obs_{pergunta}")
                        penalidade_acumulada += peso_penalidade
                        
                    respostas_monitoria[pergunta] = {
                        "nota": status,
                        "comentario": comentario,
                        "penalidade_aplicada": peso_penalidade if status == "NC" else 0
                    }
        return penalidade_acumulada

    # Renderiza e soma as penalidades de cada aba
    penalidades_n1 = render_perguntas(criterios_n1, 1, tab_n1)
    penalidades_n2 = render_perguntas(criterios_n2, 3, tab_n2)
    penalidades_n3 = render_perguntas(criterios_n3, 7, tab_n3)

    total_penalidades = penalidades_n1 + penalidades_n2 + penalidades_n3

    # ==========================================================
    # 🧮 CÁLCULO DA NOTA FINAL E SUBMISSÃO
    # ==========================================================
    st.write("---")
    
    # A nota começa sempre em 100 e subtrai as penalidades
    nota_final = max(0, 100 - total_penalidades)
    
    col_nota, col_obs = st.columns([1, 2])
    
    with col_nota:
        cor_nota = "#00E676" if nota_final >= 90 else "#FFB300" if nota_final >= 80 else "#FF4B4B"
        st.markdown(
            f"""
            <div style="background-color: {cor_nota}22; border: 2px solid {cor_nota}; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="margin:0; color: {cor_nota};">Índice de Qualidade</h3>
                <h1 style="margin:0; font-size: 48px; color: {cor_nota};">{nota_final}%</h1>
            </div>
            """, unsafe_allow_html=True
        )
        
    with col_obs:
        observacoes_gerais = st.text_area("Comentários Gerais ou Feedback para o SDR:", height=130, key="observacoes_gerais_widget")

    st.write("##")

    # BOTÃO DE SALVAR
    if st.button("💾 Salvar Monitoria e Aplicar Nota", type="primary", use_container_width=True):
            
        # Validação: Obrigar justificativa para as Não Conformidades (NC)
        falta_comentario = False
        for p, dados in respostas_monitoria.items():
            if dados["nota"] == "NC" and len(dados["comentario"].strip()) < 5:
                falta_comentario = True
                st.error("Você marcou 'Não Conforme' em um item, mas não justificou adequadamente. Verifique as abas.")
                break
                
        if falta_comentario:
            return

        with st.spinner("A guardar avaliação e a notificar o SDR..."):
            try:
                payload = {
                    "sdr": sdr_selecionado,
                    "monitor_responsavel": auditor_nome,
                    "data": str(data_avaliacao), 
                    "link_selene": link_selene,
                    "link_nectar": link_nectar,
                    "nota": nota_final,
                    "observacoes": observacoes_gerais,
                    "detalhes": respostas_monitoria,
                    "criado_em": datetime.now().isoformat(),
                    "departamento": "SDR"
                }

                resposta = supabase.table("monitorias").insert(payload).execute()

                if resposta.data:
                    # Envia notificação automática para o sininho do SDR
                    msg_notificacao = f"Sua avaliação de Qualidade foi finalizada! Nota: {nota_final}%. Acesse o histórico para ver o feedback."
                    supabase.table("notificacoes").insert({
                        "usuario": sdr_selecionado,
                        "mensagem": msg_notificacao,
                        "lida": False
                    }).execute()
                    
                    registrar_auditoria("MONITORIA", f"Avaliou {sdr_selecionado} com {nota_final}%", sdr_selecionado, auditor_nome)

                    # ==========================================================
                    # 🧼 INTEGRAÇÃO DA REGRA DE LIMPEZA DE CAMPOS (RESET)
                    # ==========================================================
                    # 1. Limpa as caixas de respostas dinâmicas (N1, N2, N3)
                    for pergunta in criterios_n1 + criterios_n2 + criterios_n3:
                        key_radio = f"radio_{pergunta}"
                        key_obs = f"obs_{pergunta}"
                        if key_radio in st.session_state:
                            del st.session_state[key_radio]
                        if key_obs in st.session_state:
                            del st.session_state[key_obs]

                    # 2. Limpa os campos fixos da tela
                    chaves_fixas_para_limpar = [
                        "sdr_selecionado_widget",
                        "link_selene_widget",
                        "link_nectar_widget",
                        "observacoes_gerais_widget"
                    ]
                    for chave in chaves_fixas_para_limpar:
                        if chave in st.session_state:
                            del st.session_state[chave]
                    
                    # O campo da data retorna automaticamente para o dia de hoje
                    if "data_avaliacao_widget" in st.session_state:
                        del st.session_state["data_avaliacao_widget"]
                    # ==========================================================

                    st.success("✅ Monitoria salva com sucesso! O SDR já foi notificado e os campos foram limpos.")
                    time.sleep(2)
                    st.rerun() # Reinicia a página limpa!
                else:
                    st.error("Erro ao salvar no banco de dados.")

            except Exception as e:
                st.error(f"Ocorreu um erro no servidor: {e}")