import streamlit as st
from database import supabase
import time

def render_notificacoes_sdr():
    nome_usuario = st.session_state.get('user_nome')
    nivel = st.session_state.get('nivel', 'SDR').upper()

    # O "Sininho" é focado no SDR para avisar sobre os vereditos
    if nivel == "SDR":
        try:
            # Procura contestações respondidas nos últimos 3 dias ou não lidas
            # Aqui fazemos um filtro simples por status finalizado
            res = supabase.table("contestacoes")\
                .select("*, monitorias(nota)")\
                .eq("sdr_nome", nome_usuario)\
                .in_("status", ["Deferido", "Indeferido"])\
                .order("criado_em", desc=True)\
                .limit(3)\
                .execute()

            if res.data:
                st.markdown("### 🔔 Novas Atualizações")
                
                for notif in res.data:
                    status = notif['status']
                    cor = "green" if status == "Deferido" else "red"
                    icone = "✅" if status == "Deferido" else "❌"
                    
                    # Criar um card de alerta estilizado
                    with st.container(border=True):
                        col_icon, col_txt = st.columns([1, 10])
                        col_icon.markdown(f"## {icone}")
                        
                        msg = f"Sua contestação da monitoria foi **{status.upper()}**!"
                        if status == "Deferido":
                            msg += f" A sua nota foi corrigida."
                        
                        col_txt.markdown(f"**{msg}**")
                        col_txt.caption(f"**Parecer do Admin:** {notif['resposta_admin']}")
                
                st.divider()
        except Exception as e:
            # Falha silenciosa para não travar a home
            pass