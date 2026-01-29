import streamlit as st
import re
from database import supabase

def validar_prefixo(prefixo):
    padrao = r'^[a-zA-Z0-9._]+$'
    return re.match(padrao, prefixo) is not None

def formatar_telefone(tel):
    numeros = re.sub(r'\D', '', tel)
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return tel

def render_cadastro():
    st.title("👥 Cadastro de Novo Colaborador")
    st.markdown("Preencha as informações abaixo. O sistema impedirá cadastros duplicados.")

    with st.container():
        nome = st.text_input("Nome Completo", placeholder="Ex: João Silva")
        usuario = st.text_input("Usuário de Login", placeholder="Ex: joao.silva")
        
        st.write("**E-mail Institucional**")
        col_pref, col_dom = st.columns([2, 1])
        with col_pref:
            prefixo_email = st.text_input("Prefixo", placeholder="rodrigo.moreira", label_visibility="collapsed")
        with col_dom:
            st.info("@grupoacelerador.com.br")
            
        telefone_raw = st.text_input("Telefone de Contato", placeholder="11999999999")
        nivel_acesso = st.selectbox("Nível de Acesso", ["SDR", "ADMIN"])
        senha = st.text_input("Senha Inicial", type="password")

    st.divider()

    if st.button("🚀 Finalizar Cadastro", use_container_width=True):
        if not nome or not usuario or not prefixo_email or not senha:
            st.error("⚠️ Preencha todos os campos obrigatórios.")
        elif not validar_prefixo(prefixo_email):
            st.error("❌ Prefixo inválido (não use espaços ou símbolos).")
        else:
            email_completo = f"{prefixo_email.strip().lower()}@grupoacelerador.com.br"
            user_clean = usuario.strip().lower()

            # --- VERIFICAÇÃO DE DUPLICIDADE ---
            # Verifica e-mail e usuário de uma vez
            check = supabase.table("usuarios").select("email, user").or_(f"email.eq.{email_completo},user.eq.{user_clean}").execute()

            if len(check.data) > 0:
                st.error(f"❌ Erro: O e-mail ou o usuário informado já está cadastrado!")
            else:
                payload = {
                    "nome": nome.strip(),
                    "user": user_clean,
                    "email": email_completo,
                    "telefone": formatar_telefone(telefone_raw),
                    "nivel": nivel_acesso.lower(),
                    "senha": senha,
                    "esta_ativo": True
                }

                try:
                    supabase.table("usuarios").insert(payload).execute()
                    st.success(f"✅ Colaborador {nome} cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {str(e)}")