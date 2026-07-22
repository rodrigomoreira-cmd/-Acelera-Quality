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
    "Utilizar canal de contato diferente do recomendado para a origem do lead."
]
CRITERIOS_N2_BACKUP = [
    "Não registrar adequadamente informações do ICP.",
    "Avançar lead sem validação completa dos critérios obrigatórios."
]
CRITERIOS_N3_BACKUP = [
    "Não iniciar contato com o lead dentro do prazo operacional definido sem justificativa válida."
]

# ==========================================================
# 🔄 FUNÇÃO PARA BUSCAR CRITÉRIOS DO BANCO (FILTRO POR DEPARTAMENTO)
# ==========================================================
def buscar_criterios_dinamicos(departamento_alvo="SDR"):
    """Busca as perguntas no Supabase filtrando pelo departamento selecionado."""
    try:
        df_crit = get_all_records_db("criterios_qa")
        if df_crit is not None and not df_crit.empty:
            
            n1, n2, n3 = [], [], []
            perguntas_vistas = set() 
            
            # Normaliza o departamento alvo para comparação
            dept_alvo_limpo = str(departamento_alvo).strip().upper()
            
            for _, row in df_crit.iterrows():
                # 1. Verifica se está ativo
                ativo = str(row.get("esta_ativo", "True")).strip().lower()
                if ativo not in ['true', '1', 't', 'yes', 'sim']:
                    continue 
                
                # 2. FILTRO DE DEPARTAMENTO (A mágica acontece aqui)
                crit_dept = str(row.get("departamento", "TODOS")).strip().upper()
                
                # Se o critério não for do departamento da pessoa E também não for para "TODOS", salta fora!
                if crit_dept != "TODOS" and crit_dept != dept_alvo_limpo and "AMBOS" not in crit_dept:
                    continue
                    
                # 3. Pega o texto da pergunta
                texto_nome = str(row.get("nome", "")).strip()
                texto_desc = str(row.get("descricao", "")).strip()
                texto_final = texto_desc if len(texto_desc) > len(texto_nome) else texto_nome
                    
                if not texto_final or texto_final.lower() == "nan":
                    continue
                
                # Filtro Anti-Duplicata
                if texto_final in perguntas_vistas:
                    continue
                perguntas_vistas.add(texto_final)
                    
                # 4. Lê grupo e peso
                grupo = str(row.get("grupo", "")).strip().upper()
                try:
                    peso_val = float(row.get("peso", 0)) 
                except:
                    peso_val = 0
                
                # 5. Distribui o critério pela aba correta
                if "N1" in grupo:
                    n1.append(texto_final)
                elif "N2" in grupo:
                    n2.append(texto_final)
                elif "N3" in grupo:
                    n3.append(texto_final)
                elif peso_val == 1:
                    n1.append(texto_final)
                elif peso_val == 3:
                    n2.append(texto_final)
                elif peso_val == 7:
                    n3.append(texto_final)
                    
            if n1 or n2 or n3:
                return n1, n2, n3
                
    except Exception as e:
        print(f"Erro ao ler os critérios do banco: {e}")
        
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
    # 🔍 BUSCA DE AVALIADOS E MAPEAMENTO DE DEPARTAMENTOS
    # ==========================================================
    df_usuarios = get_all_records_db("usuarios")
    lista_avaliados = []
    mapa_departamentos = {} # 👈 Dicionário que decora quem é SDR e quem é Especialista
    
    if df_usuarios is not None and not df_usuarios.empty:
        # Filtra apenas ativos
        if 'ativo' in df_usuarios.columns:
            df_usuarios = df_usuarios[df_usuarios['ativo'].astype(str).str.lower().isin(['true', '1', 't', 'yes', 'sim'])]
            
        if 'nome' in df_usuarios.columns:
            # Pega o nome e o departamento de cada um
            for _, row in df_usuarios.iterrows():
                nome_val = str(row['nome']).strip()
                dept_val = str(row.get('departamento', 'SDR')).strip()
                
                if nome_val and nome_val.lower() != 'nan':
                    lista_avaliados.append(nome_val)
                    mapa_departamentos[nome_val] = dept_val
            
    lista_avaliados = sorted(list(set(lista_avaliados))) if lista_avaliados else ["Nenhum usuário ativo encontrado"]

    # 1. DADOS PRINCIPAIS DA AVALIAÇÃO
    with st.container(border=True):
        st.markdown("### 👤 Dados do Avaliado")
        col1, col2 = st.columns(2)
        
        sdr_selecionado = col1.selectbox("Selecione o Avaliado:", [""] + lista_avaliados, key="sdr_selecionado_widget")
        data_avaliacao = col2.date_input("Data da Avaliação:", datetime.today(), key="data_avaliacao_widget")
        
        col_link1, col_link2 = st.columns(2)
        link_selene = col_link1.text_input("🔗 Link do Selene (Gravação):", placeholder="https://...", key="link_selene_widget")
        link_nectar = col_link2.text_input("🗂️ Link do Nectar (Card):", placeholder="https://...", key="link_nectar_widget")

    st.write("##")
    
    if not sdr_selecionado or sdr_selecionado == "Nenhum usuário ativo encontrado":
        st.info("👈 Por favor, selecione um usuário no campo acima para carregar o formulário de avaliação.")
        return 
    
    # Descobre de que departamento é a pessoa selecionada (Se não encontrar, assume SDR)
    departamento_do_avaliado = mapa_departamentos.get(sdr_selecionado, "SDR")
    st.caption(f"📌 Carregando critérios para o departamento: **{departamento_do_avaliado}**")
    
    # 👈 Busca as perguntas passando o departamento exato do colaborador selecionado!
    criterios_n1, criterios_n2, criterios_n3 = buscar_criterios_dinamicos(departamento_alvo=departamento_do_avaliado)
    
    # 2. SISTEMA DE ABAS (N1, N2, N3)
    tab_n1, tab_n2, tab_n3 = st.tabs(["🟢 N1 (Penalidade: -1%)", "🟡 N2 (Penalidade: -3%)", "🔴 N3 (Penalidade: -7%)"])
    
    respostas_monitoria = {}

    def render_perguntas(lista_perguntas, peso_penalidade, tab_context, prefixo_aba):
        penalidade_acumulada = 0
        with tab_context:
            if not lista_perguntas:
                st.info(f"Nenhum critério ativo cadastrado para {departamento_do_avaliado} neste nível.")
                
            for idx, pergunta in enumerate(lista_perguntas):
                key_radio = f"radio_{prefixo_aba}_{idx}"
                key_obs = f"obs_{prefixo_aba}_{idx}"
                
                with st.container(border=True):
                    st.markdown(f"**📌 {pergunta}**")
                    
                    status = st.radio(
                        "Avaliação:",
                        options=["C", "NC", "NSA"],
                        index=0, 
                        key=key_radio,
                        horizontal=True,
                        format_func=lambda x: "✅ Conforme" if x == "C" else "❌ Não Conforme" if x == "NC" else "➖ Não Se Aplica (NSA)",
                        label_visibility="collapsed"
                    )
                    
                    comentario = ""
                    if status == "NC":
                        st.warning(f"⚠️ Penalidade de -{peso_penalidade}% será aplicada.")
                        comentario = st.text_area("Motivo da Não Conformidade (Obrigatório):", key=key_obs)
                        penalidade_acumulada += peso_penalidade
                        
                    respostas_monitoria[f"{prefixo_aba}_{idx}"] = {
                        "criterio": pergunta, 
                        "nota": status,
                        "comentario": comentario,
                        "penalidade_aplicada": peso_penalidade if status == "NC" else 0
                    }
        return penalidade_acumulada

    penalidades_n1 = render_perguntas(criterios_n1, 1, tab_n1, "n1")
    penalidades_n2 = render_perguntas(criterios_n2, 3, tab_n2, "n2")
    penalidades_n3 = render_perguntas(criterios_n3, 7, tab_n3, "n3")

    total_penalidades = penalidades_n1 + penalidades_n2 + penalidades_n3

    st.write("---")
    
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
        observacoes_gerais = st.text_area("Comentários Gerais ou Feedback para o Avaliado:", height=130, key="observacoes_gerais_widget")

    st.write("##")

    if st.button("💾 Salvar Monitoria e Aplicar Nota", type="primary", use_container_width=True):
            
        falta_comentario = False
        for p, dados in respostas_monitoria.items():
            if dados["nota"] == "NC" and len(dados["comentario"].strip()) < 5:
                falta_comentario = True
                st.error("Você marcou 'Não Conforme' em um item, mas não justificou adequadamente. Verifique as abas.")
                break
                
        if falta_comentario:
            return

        with st.spinner("A guardar avaliação e a notificar o usuário..."):
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
                    "departamento": departamento_do_avaliado # Salva corretamente de qual departamento era
                }

                resposta = supabase.table("monitorias").insert(payload).execute()

                if resposta.data:
                    msg_notificacao = f"Sua avaliação de Qualidade foi finalizada! Nota: {nota_final}%. Acesse o histórico para ver o feedback."
                    supabase.table("notificacoes").insert({
                        "usuario": sdr_selecionado,
                        "mensagem": msg_notificacao,
                        "lida": False
                    }).execute()
                    
                    registrar_auditoria("MONITORIA", f"Avaliou {sdr_selecionado} com {nota_final}%", sdr_selecionado, auditor_nome)

                    chaves_memoria = list(st.session_state.keys())
                    for k in chaves_memoria:
                        if k.startswith("radio_n") or k.startswith("obs_n"):
                            del st.session_state[k]

                    chaves_fixas = ["sdr_selecionado_widget", "link_selene_widget", "link_nectar_widget", "observacoes_gerais_widget", "data_avaliacao_widget"]
                    for chave in chaves_fixas:
                        if chave in st.session_state:
                            del st.session_state[chave]

                    st.success("✅ Monitoria salva com sucesso! O Avaliado já foi notificado e a tela foi limpa.")
                    time.sleep(2)
                    st.rerun() 
                else:
                    st.error("Erro ao salvar no banco de dados.")

            except Exception as e:
                st.error(f"Ocorreu um erro no servidor: {e}")