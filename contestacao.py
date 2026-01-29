import streamlit as st
from database import supabase
import pandas as pd

def render_contestacao():
    st.title("⚖️ Central de Contestações")
    st.markdown("Visualize o histórico completo e responda às solicitações de revisão.")

    # 1. Busca TODAS as contestações no banco
    try:
        res_all = supabase.table("contestacoes").select("*").order("id", desc=True).execute()
        todas_contestacoes = res_all.data
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return

    if not todas_contestacoes:
        st.info("Nenhuma contestação registrada no sistema ainda.")
        return

    df = pd.DataFrame(todas_contestacoes)

    # --- SEÇÃO 1: FILTRO E HISTÓRICO GERAL ---
    st.subheader("📊 Filtro de Busca")
    sdrs_disponiveis = sorted(df['sdr'].unique().tolist())
    sdr_filtro = st.selectbox("🔍 Selecione um SDR para filtrar as tabelas:", ["Todos"] + sdrs_disponiveis)

    df_filtrado = df.copy()
    if sdr_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['sdr'] == sdr_filtro]

    # --- SEÇÃO 2: RESPOSTA (Apenas para as Pendentes) ---
    st.divider()
    st.subheader("📝 Responder Contestações Pendentes")
    
    pendentes = [c for c in todas_contestacoes if c['status'] == "Pendente"]
    
    if not pendentes:
        st.success("🎉 Todas as contestações pendentes foram respondidas!")
    else:
        # Mostra apenas as pendentes do SDR filtrado se houver filtro
        opcoes_pendentes = [f"ID: {c['id']} | SDR: {c['sdr']}" for c in pendentes if sdr_filtro == "Todos" or c['sdr'] == sdr_filtro]
        
        if not opcoes_pendentes:
            st.info(f"Nenhuma contestação pendente para {sdr_filtro}.")
        else:
            opcoes_dict = {f"ID: {c['id']} | SDR: {c['sdr']}": c for c in pendentes}
            escolha = st.selectbox("Selecione uma pendente para analisar:", ["Selecione..."] + opcoes_pendentes)

            if escolha != "Selecione...":
                dados = opcoes_dict[escolha]
                id_contestacao = dados['id']
                
                with st.container(border=True):
                    st.write(f"**Analisando Pedido #{id_contestacao}**")
                    st.info(f"**Motivo do SDR:** {dados['motivo']}")
                    
                    with st.form(key=f"form_resp_{id_contestacao}", clear_on_submit=True):
                        col_d1, col_d2 = st.columns(2)
                        decisao_final = col_d1.radio("Resultado:", ["Mantida", "Procedente (Alterar Nota)", "Improcedente"])
                        
                        justificativa = st.text_area("Justificativa Final:")
                        
                        if st.form_submit_button("Confirmar e Salvar Decisão"):
                            if not justificativa:
                                st.warning("A justificativa é obrigatória.")
                            else:
                                try:
                                    supabase.table("contestacoes").update({
                                        "status": "Respondida",
                                        "decisao_gestao": decisao_final,
                                        "justificativa_gestao": justificativa,
                                        "respondido_em": "now()"
                                    }).eq("id", id_contestacao).execute()
                                    
                                    # REGISTRO NA AUDITORIA
                                    supabase.table("auditoria").insert({
                                        "admin_responsavel": st.session_state.get('user_nome'),
                                        "colaborador_afetado": dados['sdr'],
                                        "acao": "CONTESTAÇÃO RESPONDIDA",
                                        "detalhes": f"Decisão: {decisao_final} para a monitoria ID {dados.get('monitoria_id')}"
                                    }).execute()

                                    st.success("Decisão gravada!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")

    # --- SEÇÃO 3: TABELA DE CONTESTAÇÕES FINALIZADAS ---
    st.divider()
    st.subheader("✅ Histórico de Decisões Finalizadas")
    
    df_finalizadas = df_filtrado[df_filtrado['status'] == "Respondida"].copy()

    if df_finalizadas.empty:
        st.info("Nenhuma decisão finalizada para exibir com os filtros atuais.")
    else:
        st.dataframe(
            df_finalizadas[['id', 'sdr', 'monitoria_id', 'decisao_gestao', 'justificativa_gestao', 'respondido_em']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "ID",
                "sdr": "SDR",
                "monitoria_id": "ID Monitoria",
                "decisao_gestao": st.column_config.TextColumn("Resultado Final", width="small"),
                "justificativa_gestao": st.column_config.TextColumn("Parecer da Gestão", width="large"),
                "respondido_em": st.column_config.DatetimeColumn("Data da Resposta", format="DD/MM/YYYY HH:mm")
            }
        )