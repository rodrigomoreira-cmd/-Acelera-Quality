import streamlit as st
import pandas as pd
from database import supabase

def render_notificacoes_contestacao():
    nome_usuario = st.session_state.get('user_nome')
    nivel = st.session_state.get('nivel', 'SDR').upper()

    # Notificações são focadas no SDR
    if nivel == "SDR":
        try:
            # Busca contestações respondidas (Deferido ou Indeferido) 
            # que o SDR ainda não "limpou" ou que foram respondidas nos últimos 3 dias
            res = supabase.table("contestacoes")\
                .select("id, status, resposta_admin, monitoria_id")\
                .eq("sdr_nome", nome_usuario)\
                .in_("status", ["Deferido", "Indeferido"])\
                .execute()

            if res.data:
                st.markdown("### 🔔 Avisos Importantes")
                for notificacao in res.data:
                    status = notificacao['status']
                    cor = "green" if status == "Deferido" else "red"
                    icone = "✅" if status == "Deferido" else "❌"
                    
                    # Exibe um alerta visual estilizado
                    with st.container(border=True):
                        st.markdown(f"""
                        {icone} **Sua contestação da monitoria #{notificacao['monitoria_id']} foi {status.upper()}!**
                        
                        **Parecer do Admin:** {notificacao['resposta_admin']}
                        """)
                        
                st.divider()
        except Exception as e:
            # Falha silenciosa para não quebrar a Home se houver erro de rede
            pass

def render_home():
    st.title(f"Bem-vindo, {st.session_state.get('user_nome', 'Usuário')}! 🚀")
    
    # Chamada do componente de notificações
    render_notificacoes_contestacao()
    
    # Restante do seu código da Home (Dashboards resumidos, etc)
    st.write("Selecione uma opção no menu lateral para começar.")