import streamlit as st
import pandas as pd
from database import supabase, get_all_records_db

def render_contestacao():
    st.title("⚖️ Central de Contestações")
    
    nivel = st.session_state.get('nivel', 'sdr').upper()
    df = get_all_records_db("monitorias")
    
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return

    # Filtro: SDR só vê as dele. ADM vê apenas as que FORAM contestadas.
    if nivel == 'SDR':
        df = df[df['sdr'] == st.session_state.user]
    else:
        df = df[df['contestada'] == True]

    for index, row in df.iterrows():
        status = row.get('status_contestacao', 'Pendente')
        cor_status = "🟠" if status == "Pendente" else "🟢" if status == "Deferido" else "🔴"
        
        with st.expander(f"{cor_status} Status: {status} | Data: {row['data']} | SDR: {row['sdr']}"):
            st.write(f"**Nota Original:** {row['nota']}%")
            st.write(f"**Motivo do SDR:** {row['motivo_contestacao']}")
            
            # --- VISÃO DO SDR (Ver Resposta) ---
            if nivel == "SDR":
                if row.get('resposta_gestor'):
                    st.markdown(f"---")
                    st.markdown(f"**💬 Resposta do Gestor:**")
                    st.info(row['resposta_gestor'])
                else:
                    st.write("⏳ *Aguardando resposta do gestor...*")
            
            # --- VISÃO DO ADM (Responder) ---
            else:
                st.markdown("---")
                if row.get('resposta_gestor'):
                    st.success(f"**Sua Resposta:** {row['resposta_gestor']}")
                
                # Botão para (re)responder
                with st.popover("RESPONDER CONTESTAÇÃO"):
                    novo_status = st.selectbox("Decisão", ["Deferido", "Indeferido"], key=f"status_{row['id']}")
                    resposta = st.text_area("Escreva a justificativa:", key=f"res_{row['id']}")
                    
                    if st.button("Enviar Resposta", key=f"btn_res_{row['id']}"):
                        try:
                            supabase.table("monitorias").update({
                                "resposta_gestor": resposta,
                                "status_contestacao": novo_status
                            }).eq("id", row['id']).execute()
                            
                            st.success("Resposta enviada!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

# Dentro de historico.py ou contestacao.py

def render_historico_sdr():
    st.title("📜 Meu Histórico de Contestações")
    st.write("Visualize o status das suas solicitações. (Somente Leitura)")

    df = get_all_records_db("monitorias")
    
    if not df.empty:
        # Filtra apenas dados do usuário logado e que foram contestados
        df_user = df[(df['sdr'] == st.session_state.user) & (df['contestada'] == True)]
        
        if df_user.empty:
            st.info("Você ainda não possui contestações registradas.")
        else:
            # Seleciona apenas colunas relevantes para o SDR
            colunas_exibicao = ["data", "nota", "motivo_contestacao", "observacoes"]
            st.dataframe(
                df_user[colunas_exibicao], 
                use_container_width=True, 
                hide_index=True
            )
    else:
        st.warning("Nenhum dado encontrado.")