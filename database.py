import streamlit as st
import pandas as pd
from supabase import create_client

# Inicialização global para evitar erro de "name not defined"
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def get_all_records_db(table_name):
    """Busca todos os registros de uma tabela no Supabase."""
    try:
        response = supabase.table(table_name).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao acessar {table_name}: {e}")
        return pd.DataFrame()

def get_criterios_ativos():
    """Busca critérios ativos na tabela config_criterios."""
    try:
        # Filtra pela coluna 'ativo' conforme seu banco
        response = supabase.table("config_criterios").select("*").eq("ativo", True).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

def save_monitoria(dados):
    """Salva a monitoria na tabela monitorias."""
    return supabase.table("monitorias").insert(dados).execute()