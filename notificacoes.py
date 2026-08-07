import streamlit as st
from database import supabase

def render_notificacoes_sdr():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        return
    # ------------------------------------------------------------------

    nome_usuario = st.session_state.get('user_nome')
    nivel = st.session_state.get('nivel', 'SDR').upper()

    # O "Sininho" é focado na operação para avisar sobre os vereditos
    if nivel not in ["ADMIN", "GESTAO", "GERENCIA", "AUDITOR"]:
        try:
            # Procura contestações respondidas nos últimos 3 dias ou não lidas
            # 👇 CORREÇÃO: Busca contestações com os status exatos ("Aceita" ou "Recusada")
            res = supabase.table("contestacoes")\
                .select("id, status, resposta_admin, monitoria_id")\
                .eq("sdr_nome", nome_usuario)\
                .in_("status", ["Aceita", "Recusada"])\
                .order("id", desc=True)\
                .limit(3)\
                .execute() # type: ignore

            if res.data:
                st.markdown("### 🔔 Novas Atualizações")
                
                for notif in res.data:
                    status = notif['status']
                    
                    if status == "Aceita":
                        cor = "#00E676"  # Verde Sucesso
                        icone = "✅"
                        txt_status = "ACEITA"
                        msg_extra = "A sua nota foi corrigida."
                    else:
                        cor = "#FF4B4B"  # Vermelho Falha
                        icone = "❌"
                        txt_status = "RECUSADA"
                        msg_extra = "A nota original foi mantida."
                    
                    # Criar um card de alerta estilizado premium
                    html_alerta = f"""
                    <div style='background-color: rgba(255,255,255,0.02); padding: 15px; border-radius: 10px; border-left: 5px solid {cor}; border-top: 1px solid rgba(255,255,255,0.05); border-right: 1px solid rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 15px;'>
                        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 10px;'>
                            <span style='font-size: 20px;'>{icone}</span>
                            <span style='font-size: 16px; font-weight: 600; color: #fff;'>Sua contestação (Monitoria #{notif['monitoria_id']}) foi {txt_status}! {msg_extra}</span>
                        </div>
                        <div style='font-size: 14px; color: #aaa; margin-left: 35px;'>
                            <strong style='color: #eee;'>Parecer da Liderança/Admin:</strong><br>
                            "{notif['resposta_admin']}"
                        </div>
                    </div>
                    """
                    st.markdown(html_alerta, unsafe_allow_html=True)
                
                st.divider()
        except Exception:
            # Falha silenciosa para não travar a interface
            pass