import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria, get_all_records_db
from datetime import datetime
import time

def render_historico_monitorias():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados.")
        return
    # ------------------------------------------------------------------

    COR_PRINCIPAL = "#FF7A00"
    usuario_logado = str(st.session_state.get("user_nome", "Gestor/Sistema"))

    st.markdown(f"<h1 style='color: {COR_PRINCIPAL};'>📊 Histórico e Feedbacks (1:1)</h1>", unsafe_allow_html=True)
    st.write("Acompanhe as monitorias realizadas e registre os feedbacks aplicados à equipe.")
    st.divider()

    # ==========================================================
    # 1. BUSCAR AS MONITORIAS NO BANCO DE DADOS
    # ==========================================================
    with st.spinner("A carregar histórico..."):
        try:
            # Traz as últimas 100 monitorias ordenadas das mais recentes para as mais antigas
            res = supabase.table("monitorias").select("*").order("criado_em", desc=True).limit(100).execute()  # type: ignore
            
            if not hasattr(res, 'data') or not res.data:
                st.info("Nenhuma monitoria encontrada no banco de dados ainda.")
                return
                
            df_monitorias = pd.DataFrame(res.data)
            
            # Formata a data para ficar bonita na tela (DD/MM/YYYY) - Corrigido para 'criado_em'
            col_data = 'criado_em' if 'criado_em' in df_monitorias.columns else 'data'
            df_monitorias['data_formatada'] = pd.to_datetime(df_monitorias[col_data], errors='coerce').dt.strftime('%d/%m/%Y')
            
        except Exception as e:
            st.error(f"Erro ao buscar histórico: {e}")
            return

    # ==========================================================
    # 2. SELEÇÃO DA MONITORIA
    # ==========================================================
    st.markdown("### 🔍 Selecione uma Avaliação")
    
    # Cria uma lista formatada para o selectbox: "Data - Nome - Nota%"
    opcoes_display = [""] + [
        f"[{row['data_formatada']}] {row['sdr']} - Nota: {row['nota']}% (Auditor: {row['monitor_responsavel']})"
        for _, row in df_monitorias.iterrows()
    ]
    
    # Usa o índice para saber qual linha do banco o usuário escolheu
    escolha = st.selectbox("Busque por nome, data ou auditor:", opcoes_display)

    if not escolha:
        st.info("👈 Selecione uma monitoria acima para ver os detalhes e dar o feedback.")
        return

    # Encontra os dados exatos da monitoria selecionada
    indice_escolhido = opcoes_display.index(escolha) - 1
    monitoria_selecionada = df_monitorias.iloc[indice_escolhido]
    id_monitoria = str(monitoria_selecionada['id'])

    st.write("##")

    # ==========================================================
    # 3. EXIBIÇÃO DOS DETALHES (DUAS COLUNAS)
    # ==========================================================
    col_detalhes, col_feedback = st.columns([1.2, 1])

    # COLUNA ESQUERDA: O QUE O AUDITOR APONTOU
    with col_detalhes:
        st.markdown("#### 📋 Detalhes da Avaliação")
        
        # Mostra a nota com cor dinâmica
        nota = float(monitoria_selecionada['nota'])
        cor_nota = "#00E676" if nota >= 90 else "#FFB300" if nota >= 80 else "#FF4B4B"
        st.markdown(f"**Nota Final:** <span style='color:{cor_nota}; font-size:20px; font-weight:bold;'>{nota}%</span>", unsafe_allow_html=True)
        
        # Links Rápidos
        link_s = str(monitoria_selecionada.get('link_selene', ''))
        link_n = str(monitoria_selecionada.get('link_nectar', ''))
        
        c1, c2 = st.columns(2)
        if link_s and link_s.lower() != 'nan':
            c1.markdown(f"[🔗 Gravação Selene]({link_s})")
        if link_n and link_n.lower() != 'nan':
            c2.markdown(f"[🗂️ Card Nectar]({link_n})")

        # Comentário Geral do Auditor
        obs_auditor = str(monitoria_selecionada.get('observacoes', ''))
        if obs_auditor and obs_auditor.lower() != 'nan':
            st.info(f"**🗣️ Comentário do Auditor:**\n\n{obs_auditor}")

        st.write("---")
        st.markdown("#### ❌ Pontos de Melhoria (Não Conformidades)")
        
        # Lê o JSON de detalhes salvo no banco para mostrar onde o colaborador errou
        detalhes = monitoria_selecionada.get('detalhes', {})
        encontrou_erro = False
        
        if isinstance(detalhes, dict):
            for chave, info in detalhes.items():
                # 👇 CORREÇÃO: Pega todos os tipos de erros graves e não conformidades
                if info.get('nota') in ["NC", "NGC", "NC Grave"]:
                    encontrou_erro = True
                    penalidade = info.get('penalidade_aplicada', 0)
                    with st.expander(f"⚠️ -{penalidade}% | {info.get('criterio', 'Critério não identificado')}"):
                        st.write(f"**Motivo:** {info.get('comentario', 'Sem comentário.')}")
                        
        if not encontrou_erro:
            st.success("🎉 Nenhuma Não Conformidade registrada nesta monitoria! Atendimento perfeito.")

    # COLUNA DIREITA: ÁREA EXCLUSIVA DO GESTOR
    with col_feedback:
        st.markdown("#### 🎯 Ação do Gestor (1:1)")
        
        # Resgata o feedback caso o gestor já tenha preenchido antes
        feedback_atual = str(monitoria_selecionada.get('resposta_gestor', ''))
        if feedback_atual == 'None' or feedback_atual.lower() == 'nan':
            feedback_atual = ""

        with st.form(key=f"form_feedback_{id_monitoria}"):
            st.caption("Registre o plano de ação acordado com o colaborador após analisar os erros acima.")
            
            novo_feedback = st.text_area(
                "Feedback / Plano de Ação:",
                value=feedback_atual,
                height=250,
                placeholder="Ex: Alinhado com o SDR sobre a importância de validar o ICP antes de avançar o card. Faremos um roleplay amanhã."
            )
            
            submit_btn = st.form_submit_button("💾 Salvar Feedback", type="primary", use_container_width=True)

            if submit_btn:
                if len(novo_feedback.strip()) < 5:
                    st.warning("⚠️ O feedback precisa ser mais detalhado.")
                else:
                    with st.spinner("A guardar feedback..."):
                        try:
                            # 🎯 A MÁGICA ACONTECE AQUI: Atualiza apenas a coluna 'resposta_gestor' daquela monitoria específica!
                            supabase.table("monitorias").update({
                                "resposta_gestor": str(novo_feedback).strip()
                            }).eq("id", id_monitoria).execute()  # type: ignore
                            
                            registrar_auditoria(
                                "FEEDBACK GESTOR", 
                                f"Registrou feedback para a monitoria de {monitoria_selecionada['sdr']}", 
                                str(monitoria_selecionada['sdr']), 
                                usuario_logado
                            )
                            
                            # 👇 CORREÇÃO: Limpa o cache para atualizar instantaneamente a aba de "Histórico Geral" e sumir a pendência
                            get_all_records_db.clear()
                            
                            st.success("✅ Feedback salvo com sucesso!")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")