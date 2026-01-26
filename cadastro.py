import streamlit as st
import pandas as pd
from database import supabase

def render_cadastro():
    st.title("👥 Gestão de SDRs")
    with st.form("novo_sdr_form", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        email = st.text_input("E-mail")
        telefone = st.text_input("Telefone (Senha)")
        if st.form_submit_button("CADASTRAR"):
            supabase.table("sdrs").insert({"nome": nome, "email": email, "telefone": telefone}).execute()
            supabase.table("usuarios").insert({"nome_exibicao": nome, "login_email": email, "senha": telefone, "nivel": "sdr"}).execute()
            st.success("Cadastrado!")
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    res = supabase.table("sdrs").select("*").execute()
    st.dataframe(pd.DataFrame(res.data), use_container_width=True)