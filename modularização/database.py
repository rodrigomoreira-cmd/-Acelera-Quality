import streamlit as st
from supabase import create_client, Client
import pandas as pd

@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

@st.cache_data(ttl=600)
def get_sdr_names_db():
    res = supabase.table("sdrs").select("nome").order("nome").execute()
    return [row['nome'] for row in res.data]

def get_all_records_db(table="monitorias"):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data)