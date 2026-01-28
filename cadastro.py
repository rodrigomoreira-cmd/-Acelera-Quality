import streamlit as st
import re
from database import supabase

def validar_prefixo(prefixo):
    """
    Permite apenas letras, números, pontos e sublinhados.
    Retorna True se for válido e False se houver espaços ou símbolos.
    """
    padrao = r'^[a-zA-Z0-9._]+$'
    return re.match(padrao, prefixo) is not None

def formatar_telefone(tel):
    """
    Remove caracteres não numéricos e aplica a máscara (XX) XXXXX-XXXX.
    """
    numeros = re.sub(r'\D', '', tel)
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return tel

def render_cadastro():
    st.title("👥 Cadastro de Novos Colaboradores")
    st.markdown("Preencha os dados abaixo para liberar o acesso ao sistema.")

    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome Completo")
            usuario = st.text_input("Usuário de Login (ex: nome.sobrenome)")
            senha_inicial = st.text_input("Senha Inicial", type="password")
        
        with col2:
            st.write("E-mail Institucional")
            c_mail_prefixo, c_mail_dominio = st.columns([2, 1])
            
            with c_mail_prefixo:
                email_prefixo = st.text_input("Prefixo do e-mail", placeholder="rodrigo.moreira", label_visibility="collapsed")
            
            with c_mail_dominio:
                st.info("@grupoacelerador.com.br")
            
            telefone_raw = st.text_input("Telefone (com DDD)", placeholder="11999999999")
            nivel = st.selectbox("Nível de Acesso", ["SDR", "ADMIN"])

        if st.form_submit_button("Finalizar Cadastro"):
            # Validações de segurança
            if not nome or not usuario or not email_prefixo or not senha_inicial:
                st.error("❌ Por favor, preencha todos os campos obrigatórios.")
            
            elif not validar_prefixo(email_prefixo):
                st.error("❌ O prefixo do e-mail é inválido! Não use espaços, acentos ou símbolos (apenas letras, números, '.' e '_').")
            
            else:
                # Processamento dos dados
                email_completo = f"{email_prefixo.strip().lower()}@grupoacelerador.com.br"
                telefone_formatado = formatar_telefone(telefone_raw)
                
                payload = {
                    "nome": nome,
                    "user": usuario.lower().strip(),
                    "senha": senha_inicial,
                    "email": email_completo,
                    "telefone": telefone_formatado,
                    "nivel": nivel.lower(),
                    "esta_ativo": True
                }

                try:
                    supabase.table("usuarios").insert(payload).execute()
                    st.success(f"✅ Usuário {nome} cadastrado com sucesso!")
                    st.info(f"📧 E-mail: {email_completo} | 📱 Tel: {telefone_formatado}")
                except Exception as e:
                    st.error(f"Erro ao cadastrar no banco: {e}")

    # Exibição da Lista de Usuários Existentes
    st.divider()
    st.subheader("📋 Colaboradores Cadastrados")
    try:
        res = supabase.table("usuarios").select("nome, user, email, telefone, nivel").execute()
        if res.data:
            st.table(res.data)
    except:
        st.info("Não foi possível carregar a lista de usuários.")