import streamlit as st
import pandas as pd
from datetime import datetime
import time
from database import supabase, get_all_records_db, registrar_auditoria

def render_nova_monitoria():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados. Verifique suas credenciais.")
        return
    # ------------------------------------------------------------------

    st.markdown("<h1 style='color: #FF7A00;'>📝 Nova Monitoria de Qualidade</h1>", unsafe_allow_html=True)
    st.write("Selecione o Avaliado e o Modelo de Checklist para iniciar a auditoria.")
    st.write("---")

    auditor_nome = st.session_state.get("user_nome", "Auditor Desconhecido")
    
    # 👇 PUXA O FILTRO DA BARRA LATERAL
    dept_logado = str(st.session_state.get("departamento_selecionado", "Todos"))

    # ==========================================================
    # 🔍 BUSCA DE AVALIADOS E MODELOS DE CHECKLIST (COM FILTRO)
    # ==========================================================
    df_usuarios = get_all_records_db("usuarios")
    lista_avaliados = []
    
    if df_usuarios is not None and not df_usuarios.empty:
        # Filtra apenas ativos
        if 'ativo' in df_usuarios.columns:
            df_usuarios = df_usuarios[df_usuarios['ativo'].astype(str).str.lower().isin(['true', '1', 't', 'yes', 'sim'])]
            
        # 👇 FILTRA PELO DEPARTAMENTO DA SIDEBAR
        if dept_logado != "Todos" and 'departamento' in df_usuarios.columns:
            df_usuarios = df_usuarios[df_usuarios['departamento'].astype(str).str.upper() == dept_logado.upper()]
            
        if 'nome' in df_usuarios.columns:
            lista_avaliados = sorted(df_usuarios['nome'].dropna().unique().tolist())
            
    lista_avaliados = lista_avaliados if lista_avaliados else ["Nenhum usuário ativo encontrado no filtro atual"]

    # Busca Modelos Ativos na nova tabela
    try:
        query_modelos = supabase.table("modelos_checklist").select("*").eq("ativo", True)
        
        # 👇 FILTRA OS MODELOS PELO DEPARTAMENTO DA SIDEBAR
        if dept_logado != "Todos":
            query_modelos = query_modelos.eq("perfil", dept_logado)
            
        res_checklists = query_modelos.execute() # type: ignore
        modelos_disponiveis = res_checklists.data if res_checklists.data else []
    except:
        modelos_disponiveis = []
        st.error("⚠️ Tabela 'modelos_checklist' não encontrada ou vazia. Crie o seu primeiro modelo em 'Configuração de Critérios'.")

    # 1. DADOS PRINCIPAIS DA AVALIAÇÃO
    with st.container(border=True):
        st.markdown("### 👤 Dados da Avaliação")
        col1, col2 = st.columns(2)
        sdr_selecionado = col1.selectbox("Selecione o Avaliado:", [""] + lista_avaliados, key="sdr_selecionado_widget")
        data_avaliacao = col2.date_input("Data da Avaliação:", datetime.today(), key="data_avaliacao_widget")
        
        col_link1, col_link2 = st.columns(2)
        link_selene = col_link1.text_input("🔗 Link do Selene (Gravação):", placeholder="https://...", key="link_selene_widget")
        link_nectar = col_link2.text_input("🗂️ Link do Nectar (Card):", placeholder="https://...", key="link_nectar_widget")

        st.write("---")
        
        opcoes_modelos = {f"{m['nome']} (Versão {m['versao']}) - Perfil: {m['perfil']}": m for m in modelos_disponiveis}
        modelo_escolhido_nome = st.selectbox("📋 Selecione o Modelo de Checklist:", [""] + list(opcoes_modelos.keys()))

    st.write("##")
    
    if not sdr_selecionado or not modelo_escolhido_nome or sdr_selecionado == "Nenhum usuário ativo encontrado no filtro atual":
        st.info("👈 Por favor, selecione um usuário e um modelo de checklist acima para carregar o formulário.")
        return 
    
    # 2. CARREGAR AS PERGUNTAS DO JSON DO MODELO ESCOLHIDO
    modelo_obj = opcoes_modelos[modelo_escolhido_nome]
    perguntas_json = modelo_obj.get("perguntas", [])
    
    criterios_n1 = [p for p in perguntas_json if str(p.get("Grupo", "")).upper() == "N1"]
    criterios_n2 = [p for p in perguntas_json if str(p.get("Grupo", "")).upper() == "N2"]
    criterios_n3 = [p for p in perguntas_json if str(p.get("Grupo", "")).upper() == "N3"]
    
    # 3. SISTEMA DE ABAS (N1, N2, N3)
    tab_n1, tab_n2, tab_n3 = st.tabs(["🟢 N1 (Atenção)", "🟡 N2 (Grave)", "🔴 N3 (Crítico)"])
    
    respostas_monitoria = {}
    zerou_monitoria = False

    def render_perguntas(lista_perguntas, tab_context, prefixo_aba):
        nonlocal zerou_monitoria
        penalidade_acumulada = 0
        with tab_context:
            if not lista_perguntas:
                st.info("Nenhuma pergunta configurada para este nível neste modelo.")
                
            for idx, p_obj in enumerate(lista_perguntas):
                pergunta_texto = p_obj.get("Pergunta", "Pergunta sem texto")
                peso_penalidade = int(p_obj.get("Peso", 0))
                eh_fatal = bool(p_obj.get("Fatal", False))
                
                key_radio = f"radio_{prefixo_aba}_{idx}"
                key_obs = f"obs_{prefixo_aba}_{idx}"
                key_file = f"file_{prefixo_aba}_{idx}"
                
                with st.container(border=True):
                    badge_fatal = " 🚨 **(ERRO FATAL)**" if eh_fatal else ""
                    st.markdown(f"**📌 {pergunta_texto}**{badge_fatal}")
                    
                    status = st.radio(
                        "Avaliação:",
                        options=["C", "NC", "NSA"],
                        index=0, 
                        key=key_radio,
                        horizontal=True,
                        format_func=lambda x: "✅ Conforme" if x == "C" else "❌ Não Conforme" if x == "NC" else "➖ Não Se Aplica (NSA)",
                        label_visibility="collapsed"
                    )
                    
                    comentario, evidencia = "", None
                    if status == "NC":
                        if eh_fatal:
                            st.error(f"🚨 ERRO FATAL: A nota será zerada.")
                            zerou_monitoria = True
                        else:
                            st.warning(f"⚠️ Penalidade de -{peso_penalidade}% será aplicada.")
                        
                        comentario = st.text_area("Motivo da Não Conformidade (Obrigatório):", key=key_obs)
                        evidencia = st.file_uploader("📸 Anexar Evidência (Opcional)", type=["png", "jpg", "jpeg"], key=key_file)
                        penalidade_acumulada += peso_penalidade
                        
                    nota_tag = "NGC" if (status == "NC" and eh_fatal) else ("NC Grave" if status == "NC" and peso_penalidade >= 7 else status)

                    respostas_monitoria[f"{prefixo_aba}_{idx}"] = {
                        "criterio": pergunta_texto, 
                        "nota": nota_tag,
                        "comentario": comentario,
                        "penalidade_aplicada": 100 if (status == "NC" and eh_fatal) else (peso_penalidade if status == "NC" else 0),
                        "evidencia_obj": evidencia
                    }
        return penalidade_acumulada

    penalidades_n1 = render_perguntas(criterios_n1, tab_n1, "n1")
    penalidades_n2 = render_perguntas(criterios_n2, tab_n2, "n2")
    penalidades_n3 = render_perguntas(criterios_n3, tab_n3, "n3")

    st.write("---")
    
    total_penalidades = penalidades_n1 + penalidades_n2 + penalidades_n3
    nota_final = 0 if zerou_monitoria else max(0, 100 - total_penalidades)
    
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
            if "NC" in dados["nota"] and len(dados["comentario"].strip()) < 5:
                falta_comentario = True
                st.error("Você marcou 'Não Conforme' em um item, mas não justificou adequadamente. Verifique as abas.")
                break
                
        if falta_comentario:
            return

        with st.spinner("A guardar avaliação e a notificar o usuário..."):
            try:
                for k, v in respostas_monitoria.items():
                    ev_obj = v.pop("evidencia_obj", None) 
                    v["evidencia_anexada"] = False
                    v["url_arquivo"] = None
                    
                    if ev_obj is not None:
                        ext = ev_obj.name.split(".")[-1]
                        nome_arq = f"ev_{sdr_selecionado.replace(' ', '_').lower()}_{int(time.time())}_{k}.{ext}"
                        try:
                            supabase.storage.from_("evidencias").upload(nome_arq, ev_obj.getvalue(), file_options={"content-type": f"image/{ext}"}) # type: ignore
                            v["evidencia_anexada"] = True
                            v["url_arquivo"] = supabase.storage.from_("evidencias").get_public_url(nome_arq) # type: ignore
                        except Exception as up_e:
                            print(f"Erro no upload da evidência: {up_e}")

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
                    "departamento": modelo_obj["perfil"], 
                    "modelo_checklist_usado": modelo_escolhido_nome 
                }

                resposta = supabase.table("monitorias").insert(payload).execute() # type: ignore
                get_all_records_db.clear()

                if hasattr(resposta, "data") and resposta.data:
                    msg_notificacao = f"Sua avaliação ({modelo_obj['nome']} - {modelo_obj['versao']}) foi finalizada! Nota: {nota_final}%. Vá ao histórico ver o feedback."
                    supabase.table("notificacoes").insert({"usuario": sdr_selecionado, "mensagem": msg_notificacao, "lida": False}).execute() # type: ignore
                    registrar_auditoria("MONITORIA", f"Avaliou {sdr_selecionado} com {nota_final}% usando {modelo_obj['nome']}", sdr_selecionado, auditor_nome)

                    chaves_memoria = list(st.session_state.keys())
                    for k in chaves_memoria:
                        if k.startswith("radio_n") or k.startswith("obs_n") or k.startswith("file_n"):
                            del st.session_state[k]

                    chaves_fixas = ["sdr_selecionado_widget", "link_selene_widget", "link_nectar_widget", "observacoes_gerais_widget", "data_avaliacao_widget"]
                    for chave in chaves_fixas:
                        if chave in st.session_state:
                            del st.session_state[chave]

                    st.success("✅ Monitoria salva com sucesso! O Avaliado já foi notificado.")
                    time.sleep(2)
                    st.rerun() 
                else:
                    st.error("Erro ao salvar no banco de dados.")

            except Exception as e:
                st.error(f"Erro no servidor: {e}")