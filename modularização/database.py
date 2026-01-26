import streamlit as st
from supabase import create_client, Client
import pandas as pd


# database.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection() -> Client:
    # Tenta ler do formato direto primeiro, depois do formato de seção
    if "SUPABASE_URL" in st.secrets:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    elif "connections" in st.secrets and "supabase" in st.secrets["connections"]:
        url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
        key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    else:
        st.error("Erro: A chave 'SUPABASE_URL' não foi encontrada nos segredos.")
        st.stop()
        
    return create_client(url, key)

supabase = init_connection()

@st.cache_data(ttl=600)
def get_sdr_names_db():
    res = supabase.table("sdrs").select("nome").order("nome").execute()
    return [row['nome'] for row in res.data]

def get_all_records_db(table="monitorias"):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data)