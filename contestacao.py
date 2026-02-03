import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import supabase

# ==========================================================
# 🛑 FUNÇÃO DO POPUP (MODAL)
# ==========================================================
@st.dialog("📝 Nova Contestação")
def abrir_modal_contestacao(monitoria_id, sdr_nome, nota, data_monitoria, obs_monitor):
    st.caption("Preencha os detalhes abaixo para enviar para análise da gestão.")
    
    # Exibe resumo visual no topo do popup
    c1, c2 = st.columns(2)
    c1.metric("Nota Original", f"{nota}%")
    c2.markdown(f"**Data:** {data_monitoria}<br>**Monitor:** {obs_monitor.split('|')[0] if '|' in obs_monitor else 'Gestão'}", unsafe_allow_html=True)
    
    st.info(f"🔎 **Observação:** {obs_monitor}")

    # Formulário dentro do Popup
    with st.form("form_modal_contestacao"):
        motivo = st.text_area("Motivo da Contestação:", placeholder="Explique detalhadamente onde houve erro na avaliação...", height=150)
        
        # Botão de envio
        enviar = st.form_submit_button("🚀 Enviar Contestação", type="primary", use_container_width=True)

        if enviar:
            if len(motivo) < 10:
                st.warning("⚠️ O motivo deve ter pelo menos 10 caracteres.")
            else:
                try:
                    # 1. Cria o registro na tabela de contestações
                    payload = {
                        "monitoria_id": monitoria_id,
                        "sdr_nome": sdr_nome,
                        "motivo": motivo,
                        "status": "Pendente",
                        "visualizada": False 
                    }
                    supabase.table("contestacoes").insert(payload).execute()
                    
                    # 2. Atualiza a monitoria para marcar que foi contestada
                    supabase.table("monitorias").update({"contestada": True}).eq("id", monitoria_id).execute()
                    
                    st.success("Enviado com sucesso!")
                    time.sleep(1)
                    st.rerun() # Isso fecha o modal e atualiza a página de fundo
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

# ==========================================================
# 🖥️ RENDERIZAÇÃO DA PÁGINA PRINCIPAL
# ==========================================================
def render_contestacao():
    st.title("⚖️ Central de Contestação")

    # Recupera dados da sessão
    nivel = st.session_state.get('nivel', 'SDR').upper()
    usuario_nome = st.session_state.get('user_nome', '')

    # ----------------------------------------------------------
    # VISÃO DO SDR
    # ----------------------------------------------------------
    if nivel == "SDR":
        st.subheader("Minhas Monitorias Recentes")
        
        try:
            # Busca apenas monitorias NÃO contestadas
            res = supabase.table("monitorias").select("*")\
                .eq("sdr", usuario_nome)\
                .eq("contestada", False)\
                .order("criado_em", desc=True)\
                .execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except Exception as e:
            st.error("Erro ao conectar ao banco.")
            return

        if df.empty:
            st.info("🎉 Nenhuma monitoria pendente para contestação.")
            return

        # Renderiza Cards
        for index, row in df.iterrows():
            with st.container(border=True):
                # Tratamento de Data Seguro
                try:
                    data_obj = pd.to_datetime(row['criado_em'])
                    if data_obj.tzinfo:
                        data_obj = data_obj.replace(tzinfo=None)
                except:
                    data_obj = datetime.now()

                # Formata data para string bonita
                data_str = data_obj.strftime('%d/%m/%Y %H:%M')

                # Cálculo de dias passados
                agora = datetime.now()
                dias_passados = (agora - data_obj).days
                
                # Layout do Card
                c1, c2, c3 = st.columns([1, 3, 1])
                
                with c1:
                    st.metric("Nota", f"{row['nota']}%")
                
                with c2:
                    st.markdown(f"**Data:** {data_str}")
                    st.markdown(f"**Monitor:** {row['monitor_responsavel']}")
                    obs = row['observacoes'] if row['observacoes'] else "-"
                    st.caption(f"Obs: {obs[:60]}..." if len(obs) > 60 else obs)

                with c3:
                    # Regra dos 3 Dias
                    if dias_passados > 3:
                        st.error("🚫 Expirado")
                        st.caption("Prazo > 3 dias")
                    else:
                        st.success("✅ No Prazo")
                        
                        # AQUI ESTÁ A MÁGICA DO POPUP
                        if st.button("Contestar 📝", key=f"btn_{row['id']}", use_container_width=True):
                            abrir_modal_contestacao(
                                monitoria_id=row['id'],
                                sdr_nome=usuario_nome,
                                nota=row['nota'],
                                data_monitoria=data_str,
                                obs_monitor=row.get('observacoes', '')
                            )

    # ----------------------------------------------------------
    # VISÃO DO ADMIN
    # ----------------------------------------------------------
    elif nivel == "ADMIN":
        st.subheader("Gerenciar Contestações")
        status_filter = st.radio("Status:", ["Pendente", "Aprovado", "Rejeitado"], horizontal=True)
        
        try:
            res = supabase.table("contestacoes").select("*").eq("status", status_filter).order("criado_em", desc=True).execute()
            df_cont = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except:
            st.error("Erro de conexão.")
            return

        if df_cont.empty:
            st.info(f"Nenhuma contestação {status_filter}.")
            return

        for index, row in df_cont.iterrows():
            with st.expander(f"{row['sdr_nome']} | {pd.to_datetime(row['criado_em']).strftime('%d/%m')}", expanded=(status_filter=="Pendente")):
                st.write(f"**Motivo:** {row['motivo']}")
                
                if status_filter == "Pendente":
                    with st.form(key=f"julgar_{row['id']}"):
                        resp = st.text_area("Resposta da Gestão:")
                        c_ok, c_no = st.columns(2)
                        
                        aprovado = c_ok.form_submit_button("✅ Aceitar", use_container_width=True)
                        rejeitado = c_no.form_submit_button("🚫 Rejeitar", use_container_width=True)

                        if aprovado:
                            supabase.table("contestacoes").update({
                                "status": "Aprovado", 
                                "resposta_admin": resp,
                                "data_resolucao": datetime.now().isoformat(),
                                "visualizada": False
                            }).eq("id", row['id']).execute()
                            st.success("Aprovado!"); time.sleep(1); st.rerun()
                            
                        if rejeitado:
                            supabase.table("contestacoes").update({
                                "status": "Rejeitado", 
                                "resposta_admin": resp,
                                "data_resolucao": datetime.now().isoformat(),
                                "visualizada": False
                            }).eq("id", row['id']).execute()
                            st.error("Rejeitado!"); time.sleep(1); st.rerun()
                else:
                    st.write(f"**Gestão:** {row.get('resposta_admin')}")