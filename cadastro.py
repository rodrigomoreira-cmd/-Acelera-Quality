import streamlit as st
import pandas as pd
from database import supabase

def render_cadastro():
    st.title("👥 Cadastro de Novos Usuários")
    st.write("Utilize este formulário para registrar novos SDRs ou Administradores no sistema.")

    with st.form("form_novo_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        nome = col1.text_input("Nome Completo")
        usuario = col2.text_input("Nome de Usuário (Login)")
        
        senha = col1.text_input("Senha", type="password")
        
        # --- NOVO CAMPO: SELEÇÃO DE NÍVEL ---
        nivel = col2.selectbox(
            "Nível de Acesso",
            options=["sdr", "admin"],
            format_func=lambda x: "SDR (Operacional)" if x == "sdr" else "Administrador (Gestão)"
        )
        
        email = st.text_input("E-mail (Opcional)")

        if st.form_submit_button("Cadastrar Usuário"):
            if not nome or not usuario or not senha:
                st.error("Por favor, preencha todos os campos obrigatórios.")
            else:
                try:
                    # Envia os dados para o Supabase, incluindo o nível escolhido
                    payload = {
                        "nome": nome,
                        "user": usuario,
                        "senha": senha,
                        "nivel": nivel, # Valor: 'sdr' ou 'admin'
                        "email": email
                    }
                    
                    supabase.table("usuarios").insert(payload).execute()
                    
                    st.success(f"Usuário {nome} cadastrado com sucesso como {nivel.upper()}!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao cadastrar no banco de dados: {e}")

    st.divider()
    st.subheader("Usuários Cadastrados")
    # Opcional: Mostrar lista de usuários atuais
    try:
        users_list = supabase.table("usuarios").select("nome, user, nivel").execute()
        if users_list.data:
            st.table(users_list.data)
    except:
        pass