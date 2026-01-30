import streamlit as st
import pandas as pd
from supabase import create_client

# --- INICIALIZAÇÃO GLOBAL ---
@st.cache_resource
def init_connection():
    """Inicializa a conexão com o Supabase usando cache para performance."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao configurar o Supabase. Verifique os Secrets: {e}")
        return None

supabase = init_connection()

def get_all_records_db(tabela):
    """Busca registros de qualquer tabela ordenados pelos mais recentes."""
    try:
        res = supabase.table(tabela).select("*").order("criado_em", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        print(f"Erro ao buscar registros em {tabela}: {e}")
        return pd.DataFrame()

def buscar_contagem_notificacoes(nome_usuario, nivel):
    """Calcula o número de itens não lidos para o Badge da Sidebar."""
    try:
        if nivel == "SDR":
            # Monitorias não visualizadas pelo SDR
            res_mon = supabase.table("monitorias").select("id", count="exact")\
                .eq("sdr", nome_usuario).eq("visualizada", False).execute()
            
            # Contestações respondidas (status != Pendente) e não visualizadas
            res_cont = supabase.table("contestacoes").select("id", count="exact")\
                .eq("sdr_nome", nome_usuario).neq("status", "Pendente").eq("visualizada", False).execute()
            
            return (res_mon.count or 0) + (res_cont.count or 0)
        else:
            # Para ADMIN: Contestações com status 'Pendente' aguardando revisão
            res = supabase.table("contestacoes").select("id", count="exact")\
                .eq("status", "Pendente").execute()
            return res.count or 0
    except:
        return 0

def registrar_auditoria(acao, colaborador_afetado, detalhes):
    """Grava logs de segurança na tabela de auditoria."""
    try:
        admin = st.session_state.get('user_nome', 'Sistema/Automático')
        payload = {
            "admin_responsavel": admin,
            "colaborador_afetado": colaborador_afetado,
            "acao": acao,
            "detalhes": detalhes
        }
        supabase.table("auditoria").insert(payload).execute()
    except Exception as e:
        print(f"Falha ao registrar auditoria: {e}")

def save_monitoria(dados):
    """Salva a monitoria e dispara o registro de auditoria."""
    try:
        # Garante que a monitoria comece como 'não lida' pelo SDR
        dados['visualizada'] = False 
        response = supabase.table("monitorias").insert(dados).execute()
        
        # Log automático na auditoria
        registrar_auditoria(
            acao="MONITORIA REALIZADA", 
            colaborador_afetado=dados.get('sdr'), 
            detalhes=f"Nota: {dados.get('nota')}% | Monitor: {dados.get('monitor_responsavel')}"
        )
        return response
    except Exception as e:
        st.error(f"Erro ao salvar monitoria: {e}")
        raise e

def get_criterios_ativos():
    """Busca critérios configurados como ativos no painel administrativo."""
    try:
        res = supabase.table("config_criterios").select("*").eq("ativo", True).execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()