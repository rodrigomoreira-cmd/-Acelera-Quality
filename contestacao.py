import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import supabase, get_all_records_db, registrar_auditoria

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

    # Mantém IDs como texto
    df_monitorias['id'] = df_monitorias['id'].astype(str).str.strip()
    df_monitorias['nota'] = pd.to_numeric(df_monitorias['nota'], errors='coerce').fillna(0).astype(int) 
    
    if 'criado_em' in df_monitorias.columns:
        df_monitorias['criado_em'] = pd.to_datetime(df_monitorias['criado_em'])

    if df_contestacoes is not None and not df_contestacoes.empty:
        df_contestacoes['id'] = df_contestacoes['id'].astype(str).str.strip()
        df_contestacoes['monitoria_id'] = df_contestacoes['monitoria_id'].astype(str).str.strip()

    # ==========================================================
    # 👤 VISÃO DO COLABORADOR (SDR / Especialista / Ingresso)
    # ==========================================================
    if nivel not in ["AUDITOR", "GESTAO", "ADMIN"]:
        st.markdown("Aqui você pode solicitar a revisão de uma nota caso discorde da avaliação recebida.")
        st.divider()

        minhas_monitorias = df_monitorias[
            df_monitorias['sdr'].astype(str).str.strip().str.upper() == nome_completo.strip().upper()
        ].copy()
        
        if minhas_monitorias.empty:
            st.success("Você ainda não possui monitorias registradas.")
            return

        seus_ids_contestados = []
        if df_contestacoes is not None and not df_contestacoes.empty:
            coluna_nome = 'sdr_nome' if 'sdr_nome' in df_contestacoes.columns else 'sdr'
            if coluna_nome in df_contestacoes.columns:
                seus_ids_contestados = df_contestacoes[
                    df_contestacoes[coluna_nome].astype(str).str.strip().str.upper() == nome_completo.strip().upper()
                ]['monitoria_id'].tolist()

        disponiveis = minhas_monitorias[~minhas_monitorias['id'].isin(seus_ids_contestados)]

        col1, col2 = st.columns([1.2, 1])

        # --- LADO ESQUERDO: ABRIR CONTESTAÇÃO ---
        with col1:
            st.subheader("📝 Abrir Nova Contestação")
            
            if disponiveis.empty:
                st.info("Você já contestou todas as monitorias disponíveis ou não possui novas avaliações.")
            else:
                opcoes_mon = {
                    f"📅 {row['criado_em'].strftime('%d/%m/%Y às %H:%M')} | Nota: {row['nota']}% | Auditor: {row['monitor_responsavel']}": row['id'] 
                    for _, row in disponiveis.iterrows()
                }
                
                escolha_label = st.selectbox("Selecione a Avaliação:", [""] + list(opcoes_mon.keys()))
                
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
                                    payload = {
                                        "monitoria_id": id_sel,
                                        "motivo": motivo_sdr,
                                        "status": "Pendente",
                                        "resposta_admin": "",
                                        "visualizada": False
                                    }
                                    coluna_nome_bd = 'sdr_nome' if df_contestacoes is not None and 'sdr_nome' in df_contestacoes.columns else 'sdr'
                                    payload[coluna_nome_bd] = nome_completo
                                        
                                    supabase.table("contestacoes").insert(payload).execute()
                                    registrar_auditoria("ABERTURA DE CONTESTAÇÃO", f"Abriu contestação para a avaliação de {auditor_nome}.", nome_completo)
                                    
                                    st.success("✅ Contestação enviada para a equipa de qualidade!")
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
                        minhas_cont['Data'] = pd.to_datetime(minhas_cont['criado_em']).dt.strftime('%d/%m/%Y')
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
    elif nivel in ["AUDITOR", "GESTAO", "ADMIN"]:
        st.markdown(f"**Caixa de Entrada - Equipe:** `{dept_selecionado}`")

        if df_contestacoes is None or df_contestacoes.empty:
            st.success("🎉 Nenhuma contestação registrada no momento.")
            return

        # -----------------------------------------------------------------
        # CORREÇÃO CRÍTICA AQUI: O 'sdr' foi adicionado nas colunas mescladas
        # -----------------------------------------------------------------
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

                    # -----------------------------------------------------------------
                    # BUSCA BLINDADA DO NOME DO COLABORADOR
                    # -----------------------------------------------------------------
                    nome_colaborador = "Desconhecido"
                    # Procura o nome em todas as colunas geradas pelo merge
                    for campo in ['sdr_y', 'sdr_x', 'sdr', 'sdr_nome']:
                        if campo in row.index and pd.notna(row[campo]) and str(row[campo]).strip().lower() != "none":
                            nome_colaborador = str(row[campo])
                            break

                    with st.expander(f"🚨 Colaborador: {nome_colaborador} | Avaliador Orig: {auditor_original} | Nota: {nota_limpa}%", expanded=True):
                        col_l, col_r = st.columns([1, 1])
                        
                        with col_l:
                            st.markdown("**Defesa do Colaborador:**")
                            st.info(f"*{row['motivo']}*")
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
                                    
                                    st.success("Julgamento registrado e auditado!")
                                    get_all_records_db.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")

            with aba_h:
                julgadas = df_completo[df_completo['status'] != "Pendente"]
                if not julgadas.empty:
                    # Busca segura para exibir na tabela de histórico
                    col_exib = 'sdr_y' if 'sdr_y' in julgadas.columns else ('sdr_x' if 'sdr_x' in julgadas.columns else ('sdr' if 'sdr' in julgadas.columns else 'sdr_nome'))
                    st.dataframe(julgadas[[col_exib, 'status', 'resposta_admin']], use_container_width=True, hide_index=True)