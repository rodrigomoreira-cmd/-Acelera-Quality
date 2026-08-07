import streamlit as st
import pandas as pd
from database import supabase

def render_notificacoes_contestacao():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        return
    # ------------------------------------------------------------------

    nome_usuario = st.session_state.get('user_nome')
    nivel = st.session_state.get('nivel', 'SDR').upper()

    # Notificações focadas na operação
    if nivel not in ["ADMIN", "GESTAO", "GERENCIA", "AUDITOR"]:
        try:
            # 👇 CORREÇÃO: Busca contestações com os status exatos ("Aceita" ou "Recusada")
            res = supabase.table("contestacoes")\
                .select("id, status, resposta_admin, monitoria_id")\
                .eq("sdr_nome", nome_usuario)\
                .in_("status", ["Aceita", "Recusada"])\
                .execute() # type: ignore

            if res.data:
                st.markdown("### 🔔 Avisos Importantes de Auditoria")
                for notificacao in res.data:
                    status = notificacao['status']
                    
                    if status == "Aceita":
                        cor = "#00E676"  # Verde Sucesso
                        icone = "✅"
                        txt_status = "ACEITA"
                    else:
                        cor = "#FF4B4B"  # Vermelho Falha
                        icone = "❌"
                        txt_status = "RECUSADA"
                    
                    # Exibe um alerta visual estilizado
                    html_alerta = f"""
                    <div style='background-color: rgba(255,255,255,0.02); padding: 15px; border-radius: 10px; border-left: 5px solid {cor}; border-top: 1px solid rgba(255,255,255,0.05); border-right: 1px solid rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 15px;'>
                        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 10px;'>
                            <span style='font-size: 20px;'>{icone}</span>
                            <span style='font-size: 16px; font-weight: 600; color: #fff;'>Sua contestação da monitoria #{notificacao['monitoria_id']} foi {txt_status}!</span>
                        </div>
                        <div style='font-size: 14px; color: #aaa; margin-left: 35px;'>
                            <strong style='color: #eee;'>Parecer da Liderança/Admin:</strong><br>
                            "{notificacao['resposta_admin']}"
                        </div>
                    </div>
                    """
                    st.markdown(html_alerta, unsafe_allow_html=True)
                        
                st.write("---")
        except Exception:
            # Falha silenciosa para não quebrar a Home se houver erro de rede
            pass

def render_home():
    st.title(f"Bem-vindo, {st.session_state.get('user_nome', 'Usuário')}! 🚀")
    
    # Chamada do componente de notificações
    render_notificacoes_contestacao()
    
    # Restante do seu código da Home (Dashboards resumidos, etc)
    st.write("Selecione uma opção no menu lateral para começar as suas atividades do dia.")