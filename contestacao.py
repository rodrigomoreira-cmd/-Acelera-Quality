import streamlit as st
import pandas as pd
import time
import pytz
from datetime import datetime
from database import supabase, get_all_records_db, registrar_auditoria

# --- IMPORT DA IA AQUI ---
from analise_ia import analisar_sentimento_texto 
# -------------------------

def render_contestacao():
    nivel = st.session_state.get('nivel', 'USUARIO')
    nome_completo = st.session_state.get('user_nome', '')
    dept_selecionado = st.session_state.get('departamento_selecionado', 'Todos')

    st.title("⚖️ Central de Contestação")

    # ==========================================================
    # 1. BUSCA E TRATAMENTO DE DADOS
    # ==========================================================
    df_monitorias = get_all_records_db("monitorias")
    df_contestacoes = get_all_records_db("contestacoes")

    if df_monitorias is None or df_monitorias.empty:
        st.info("Nenhuma monitoria encontrada no sistema.")
        return

    # Mantém IDs como texto e trata a nota
    df_monitorias['id'] = df_monitorias['id'].astype(str).str.strip()
    df_monitorias['nota'] = pd.to_numeric(df_monitorias['nota'], errors='coerce').fillna(0).astype(int) 
    
    # Padroniza a data de criação com o Fuso Horário de Brasília
    fuso = pytz.timezone('America/Sao_Paulo')
    if 'criado_em' in df_monitorias.columns:
        df_monitorias['criado_em'] = pd.to_datetime(df_monitorias['criado_em'], errors='coerce')
        
        if not df_monitorias['criado_em'].isna().all():
            if df_monitorias['criado_em'].dt.tz is None:
                df_monitorias['criado_em'] = df_monitorias['criado_em'].dt.tz_localize('UTC').dt.tz_convert(fuso)
            else:
                df_monitorias['criado_em'] = df_monitorias['criado_em'].dt.tz_convert(fuso)

    if df_contestacoes is not None and not df_contestacoes.empty:
        df_contestacoes['id'] = df_contestacoes['id'].astype(str).str.strip()
        df_contestacoes['monitoria_id'] = df_contestacoes['monitoria_id'].astype(str).str.strip()

    # ==========================================================
    # 👤 VISÃO DO COLABORADOR (SDR / Especialista / Ingresso)
    # ==========================================================
    if nivel not in ["AUDITOR", "GESTAO", "ADMIN", "GERENCIA"]:
        st.markdown("Aqui você pode solicitar a revisão de uma nota caso discorde da avaliação recebida.")
        
        st.info("⏱️ **Regra de SLA:** Você possui até **3 dias corridos** após a data da avaliação para abrir uma contestação. Após este prazo, a nota é considerada validada.")
        st.divider()

        minhas_monitorias = df_monitorias[
            df_monitorias['sdr'].astype(str).str.strip().str.upper() == nome_completo.strip().upper()
        ].copy()
        
        if minhas_monitorias.empty:
            st.success("Você ainda não possui monitorias registradas.")
            return

        hoje = datetime.now(fuso)
        minhas_monitorias['dias_passados'] = (hoje - minhas_monitorias['criado_em']).dt.days

        seus_ids_contestados = []
        if df_contestacoes is not None and not df_contestacoes.empty:
            coluna_nome = 'sdr_nome' if 'sdr_nome' in df_contestacoes.columns else 'sdr'
            if coluna_nome in df_contestacoes.columns:
                seus_ids_contestados = df_contestacoes[
                    df_contestacoes[coluna_nome].astype(str).str.strip().str.upper() == nome_completo.strip().upper()
                ]['monitoria_id'].tolist()

        disponiveis = minhas_monitorias[
            (~minhas_monitorias['id'].isin(seus_ids_contestados)) & 
            (minhas_monitorias['dias_passados'] <= 3)
        ]

        col1, col2 = st.columns([1.2, 1])

        # --- LADO ESQUERDO: ABRIR CONTESTAÇÃO ---
        with col1:
            st.subheader("📝 Abrir Nova Contestação")
            
            if disponiveis.empty:
                st.warning("🔒 Nenhuma avaliação disponível. Você já contestou as monitorias recentes ou elas passaram do prazo de 3 dias.")
            else:
                opcoes_mon = {}
                for _, row in disponiveis.iterrows():
                    dias_restantes = 3 - row['dias_passados']
                    aviso_dias = "⏳ Último dia!" if dias_restantes <= 0 else f"⏳ {dias_restantes} dia(s) restante(s)"
                    
                    dt_format = row['criado_em'].strftime('%d/%m/%Y') if pd.notna(row['criado_em']) else "Data N/D"
                    label = f"📅 {dt_format} | Nota: {row['nota']}% | Auditor: {row['monitor_responsavel']} ({aviso_dias})"
                    opcoes_mon[label] = row['id']
                
                escolha_label = st.selectbox("Selecione a Avaliação dentro do prazo:", [""] + list(opcoes_mon.keys()))
                
                if escolha_label:
                    id_sel = opcoes_mon[escolha_label]
                    mon_row = disponiveis[disponiveis['id'] == id_sel].iloc[0]
                    auditor_nome = mon_row['monitor_responsavel']

                    try:
                        res_aud = supabase.table("usuarios").select("foto_url").eq("nome", auditor_nome).execute()
                        foto_auditor = res_aud.data[0].get('foto_url') if res_aud.data else None
                    except:
                        foto_auditor = None

                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    with st.container(border=True):
                        c_foto, c_info = st.columns([1, 4])
                        with c_foto:
                            if foto_auditor:
                                st.markdown(f'<img src="{foto_auditor}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px solid #ff4b4b;">', unsafe_allow_html=True)
                            else:
                                st.markdown('<div style="font-size: 60px;">🕵️</div>', unsafe_allow_html=True)
                        
                        with c_info:
                            st.markdown(f"#### Avaliador: {auditor_nome}")
                            st.markdown(f"**Nota:** `{mon_row['nota']}%`")
                            
                        obs = mon_row.get('observacoes', '')
                        if pd.notna(obs) and obs.strip():
                            st.info(f"💬 **Mensagem do Auditor:** {obs}")

                    detalhes = mon_row.get('detalhes', {})
                    erros_encontrados = 0
                    
                    st.markdown("#### 🚨 Pontos de Melhoria Apontados")
                    
                    if detalhes and isinstance(detalhes, dict):
                        for item, info in detalhes.items():
                            if isinstance(info, dict):
                                n = info.get('nota', '')
                                if n in ["NC", "NGC", "NC Grave"]:
                                    erros_encontrados += 1
                                    with st.expander(f"❌ **{item}** (Penalidade: {n})", expanded=True):
                                        st.write(f"**Motivo do Erro:** {info.get('comentario', 'Sem justificativa.')}")
                                        
                                        if info.get('evidencia_anexada'):
                                            url_imagem = info.get('url_arquivo')
                                            nome_arquivo = info.get('arquivo', 'Anexo')
                                            if url_imagem:
                                                st.image(url_imagem, caption=f"Evidência: {nome_arquivo}", use_container_width=True)
                                                st.markdown(f"🔗 [Clique aqui para abrir a imagem original]({url_imagem})")
                                            else:
                                                st.warning(f"⚠️ O arquivo `{nome_arquivo}` foi registado, mas a exibição falhou.")
                    
                    if erros_encontrados == 0:
                        st.success("✨ Nenhum erro grave (NC/NGC) detalhado nesta monitoria.")

                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.form("form_envio_contestacao", clear_on_submit=True):
                        st.markdown("##### ✍️ Sua Defesa")
                        motivo_sdr = st.text_area("Justificativa (Obrigatório):", height=120, placeholder="Explique por que você discorda da avaliação destes itens. Se possível, cite o minuto da gravação...")
                        
                        if st.form_submit_button("🚀 Enviar Contestação", type="primary", use_container_width=True):
                            if not motivo_sdr or len(motivo_sdr) < 10:
                                st.warning("⚠️ Escreva uma justificativa clara (mínimo de 10 caracteres).")
                            else:
                                try:
                                    # --- CHAMADA DA INTELIGÊNCIA ARTIFICIAL ---
                                    with st.spinner("🤖 Processando contestação com IA..."):
                                        sent_ia, res_ia = analisar_sentimento_texto(motivo_sdr)
                                    # ------------------------------------------

                                    payload = {
                                        "monitoria_id": id_sel,
                                        "motivo": motivo_sdr,
                                        "status": "Pendente",
                                        "resposta_admin": "",
                                        "visualizada": False,
                                        "sentimento_ia": sent_ia,  # Salvando a Tag da IA
                                        "resumo_ia": res_ia        # Salvando o Resumo da IA
                                    }
                                    coluna_nome_bd = 'sdr_nome' if df_contestacoes is not None and 'sdr_nome' in df_contestacoes.columns else 'sdr'
                                    payload[coluna_nome_bd] = nome_completo
                                        
                                    supabase.table("contestacoes").insert(payload).execute()
                                    registrar_auditoria("ABERTURA DE CONTESTAÇÃO", f"Abriu contestação para a avaliação de {auditor_nome}.", nome_completo)
                                    
                                    # 🔔 GATILHO: AVISA O AUDITOR QUE ELE FOI CONTESTADO
                                    try:
                                        supabase.table("notificacoes").insert({
                                            "usuario": auditor_nome, 
                                            "mensagem": f"⚖️ {nome_completo} abriu uma contestação referente à sua avaliação. Verifique a Central de Contestações.", 
                                            "lida": False
                                        }).execute()
                                    except: pass

                                    st.success("✅ Contestação enviada para a equipe de qualidade!")
                                    time.sleep(1.5)
                                    get_all_records_db.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")

        # --- LADO DIREITO: HISTÓRICO DE CONTESTAÇÕES ---
        with col2:
            st.subheader("📊 Minhas Contestações")
            if df_contestacoes is not None and not df_contestacoes.empty:
                coluna_filtro = 'sdr_nome' if 'sdr_nome' in df_contestacoes.columns else 'sdr'
                minhas_cont = df_contestacoes[df_contestacoes[coluna_filtro].astype(str).str.strip().str.upper() == nome_completo.strip().upper()].copy()
                
                if not minhas_cont.empty:
                    if 'criado_em' in minhas_cont.columns:
                        minhas_cont['criado_em'] = pd.to_datetime(minhas_cont['criado_em'], errors='coerce')
                        minhas_cont['Data'] = minhas_cont['criado_em'].dt.strftime('%d/%m/%Y').fillna("-")
                    else:
                        minhas_cont['Data'] = "-"
                        
                    def format_status(val):
                        if val == 'Aceita': return '✅ Aceita'
                        if val == 'Recusada': return '❌ Recusada'
                        return '⏳ Pendente'
                        
                    minhas_cont['Status Vis'] = minhas_cont['status'].apply(format_status)

                    st.dataframe(
                        minhas_cont[['Data', 'Status Vis', 'resposta_admin']],
                        column_config={
                            "Data": "Data", 
                            "Status Vis": "Status", 
                            "resposta_admin": st.column_config.TextColumn("Feedback do Auditor", width="large")
                        },
                        hide_index=True, use_container_width=True
                    )
                else:
                    st.caption("Você não tem nenhuma contestação aberta no momento.")

    # ==========================================================
    # 🛡️ VISÃO DA LIDERANÇA (AUDITOR / GESTOR / ADMIN)
    # ==========================================================
    elif nivel in ["AUDITOR", "GESTAO", "ADMIN", "GERENCIA"]:
        st.markdown(f"**Caixa de Entrada - Equipe:** `{dept_selecionado}`")
        
        if df_contestacoes is None or df_contestacoes.empty:
            st.success("🎉 Nenhuma contestação registrada no momento.")
            return

        colunas_necessarias = ['id', 'sdr', 'departamento', 'nota', 'link_selene', 'link_nectar', 'detalhes', 'monitor_responsavel']
        colunas_existentes = [c for c in colunas_necessarias if c in df_monitorias.columns]

        df_completo = pd.merge(
            df_contestacoes, 
            df_monitorias[colunas_existentes], 
            left_on='monitoria_id', right_on='id', how='left'
        )

        if dept_selecionado != "Todos" and 'departamento' in df_completo.columns:
            df_completo = df_completo[df_completo['departamento'].astype(str).str.strip().str.upper() == dept_selecionado.strip().upper()]

        pendentes = df_completo[df_completo['status'] == "Pendente"]

        if pendentes.empty:
            st.success("✅ Tudo analisado! A caixa de entrada está vazia.")
        else:
            aba_p, aba_h = st.tabs(["📝 Pendentes de Análise", "📚 Histórico Julgado"])

            with aba_p:
                for _, row in pendentes.iterrows():
                    id_cont_limpo = str(row['id_x']) if 'id_x' in row.index else str(row['id'])
                    nota_limpa = int(float(str(row['nota']))) if pd.notna(row.get('nota')) else 0
                    auditor_original = row.get('monitor_responsavel', 'Desconhecido')

                    # BUSCA BLINDADA DO NOME DO COLABORADOR
                    nome_colaborador = "Desconhecido"
                    for campo in ['sdr_y', 'sdr_x', 'sdr', 'sdr_nome']:
                        if campo in row.index and pd.notna(row[campo]) and str(row[campo]).strip().lower() != "none":
                            nome_colaborador = str(row[campo])
                            break
                            
                    data_raw = row.get('criado_em_x', row.get('criado_em'))
                    if pd.notna(data_raw):
                        data_formatada = pd.to_datetime(data_raw, errors='coerce').strftime('%d/%m/%Y %H:%M')
                    else:
                        data_formatada = "Data N/D"

                    # --- PEGANDO OS DADOS DA IA PARA MOSTRAR AO GESTOR ---
                    tag_ia = row.get('sentimento_ia', '🤖 Sem IA')
                    if pd.isna(tag_ia): tag_ia = '🤖 Sem IA'
                    resumo_ia = row.get('resumo_ia', '')

                    with st.expander(f"📅 {data_formatada} | 🚨 Colab: {nome_colaborador} | Avaliador: {auditor_original} | IA: {tag_ia}", expanded=True):
                        col_l, col_r = st.columns([1, 1])
                        
                        with col_l:
                            st.markdown("**Defesa do Colaborador:**")
                            st.info(f"*{row['motivo']}*")
                            
                            # Exibe o resumo gerado pela IA se existir
                            if pd.notna(resumo_ia) and resumo_ia != "":
                                st.markdown(f"**🧠 Resumo da IA ({tag_ia}):**")
                                st.caption(f"_{resumo_ia}_")

                            if pd.notna(row.get('link_selene')): st.markdown(f"🎧 [Ouvir Gravação]({row['link_selene']})")
                            if pd.notna(row.get('link_nectar')): st.markdown(f"🗂️ [Acessar CRM]({row['link_nectar']})")

                        with col_r:
                            st.markdown("**Erros Apontados na Avaliação:**")
                            det_auditor = row.get('detalhes', {})
                            if isinstance(det_auditor, dict):
                                for item, d_info in det_auditor.items():
                                    if isinstance(d_info, dict) and d_info.get('nota') in ["NC", "NGC", "NC Grave"]:
                                        with st.container(border=True):
                                            st.error(f"**{item}**\n\nMotivo: {d_info.get('comentario')}")
                                            if d_info.get('evidencia_anexada'):
                                                url_imagem = d_info.get('url_arquivo')
                                                if url_imagem:
                                                    st.image(url_imagem, use_container_width=True)
                                                    st.markdown(f"🔗 [Abrir imagem]({url_imagem})")

                        st.divider()
                        with st.form(f"form_veredito_{id_cont_limpo}"):
                            decisao = st.radio("Resultado da Análise:", ["Aceita", "Recusada"], horizontal=True)
                            feedback = st.text_area("Feedback oficial para o colaborador:", height=100)
                            
                            if st.form_submit_button("⚖️ Salvar Decisão", type="primary", use_container_width=True):
                                try:
                                    supabase.table("contestacoes").update({
                                        "status": decisao,
                                        "resposta_admin": feedback
                                    }).eq("id", id_cont_limpo).execute()
                                    
                                    registrar_auditoria("JULGAMENTO DE CONTESTAÇÃO", f"A contestação de {nome_colaborador} foi julgada como '{decisao}'.", nome_colaborador)

                                    # ==========================================================
                                    # 🔔 GATILHOS DE COMUNICAÇÃO (AVISA O SDR)
                                    # ==========================================================
                                    try:
                                        # 1. Avisa o SDR que houve um resultado
                                        supabase.table("notificacoes").insert({
                                            "usuario": nome_colaborador,
                                            "mensagem": f"⚖️ Sua contestação foi avaliada como: {decisao}. Acesse a Central de Contestações para ler o feedback.",
                                            "lida": False
                                        }).execute()

                                        # 2. Gatilho de Gamificação (Medalha Advogado de Defesa)
                                        if decisao == "Aceita":
                                            msg_advogado = "🎖️ PARABÉNS! Sua contestação foi aceita. Você provou seu ponto e desbloqueou a medalha Advogado de Defesa!"
                                            supabase.table("notificacoes").insert({
                                                "usuario": nome_colaborador,
                                                "mensagem": msg_advogado,
                                                "lida": False
                                            }).execute()
                                    except Exception as e:
                                        print(f"Erro silencioso de notificação: {e}")
                                    
                                    st.success("Julgamento registrado e auditado!")
                                    get_all_records_db.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")

            with aba_h:
                julgadas = df_completo[df_completo['status'] != "Pendente"]
                if not julgadas.empty:
                    col_exib = 'sdr_y' if 'sdr_y' in julgadas.columns else ('sdr_x' if 'sdr_x' in julgadas.columns else ('sdr' if 'sdr' in julgadas.columns else 'sdr_nome'))
                    
                    if 'criado_em_x' in julgadas.columns:
                        julgadas['criado_em_x'] = pd.to_datetime(julgadas['criado_em_x'], errors='coerce')
                        julgadas['Data_Vis'] = julgadas['criado_em_x'].dt.strftime('%d/%m/%Y').fillna("-")
                    else:
                        julgadas['Data_Vis'] = "-"
                        
                    st.dataframe(
                        julgadas[['Data_Vis', col_exib, 'status', 'resposta_admin']], 
                        column_config={
                            "Data_Vis": "Data",
                            col_exib: "Colaborador",
                            "status": "Status",
                            "resposta_admin": "Feedback"
                        },
                        use_container_width=True, hide_index=True
                    )