import streamlit as st
import re
from database import supabase

def validar_prefixo(prefixo):
    padrao = r'^[a-zA-Z0-9._]+$'
    return re.match(padrao, prefixo) is not None

def formatar_telefone(tel):
    numeros = re.sub(r'\D', '', tel)
    if len(numeros) == 11: return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10: return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return tel

def render_usuario_gestao():
    st.title("👤 Gerenciamento de Perfil")
    
    user_logado = st.session_state.user
    nivel = st.session_state.get('nivel', 'sdr').upper()

    res = supabase.table("usuarios").select("*").eq("nome", user_logado).execute()
    if not res.data:
        st.error("Perfil não encontrado.")
        return

    dados_user = res.data[0]
    prefixo_atual = dados_user.get('email', '').split('@')[0]

    st.subheader("Meus Dados")
    st.text_input("Nome", value=dados_user['nome'], disabled=True)
    st.text_input("Usuário", value=dados_user['user'], disabled=True)
    
    st.write("**E-mail Institucional**")
    cp, cd = st.columns([2, 1])
    with cp:
        st.text_input("Prefixo", value=prefixo_atual, disabled=(nivel != "ADMIN"), label_visibility="collapsed")
    with cd:
        st.info("@grupoacelerador.com.br")
    
    st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=(nivel != "ADMIN"))

    with st.expander("🔐 Alterar Minha Senha"):
        n_senha = st.text_input("Nova Senha", type="password")
        if st.button("Atualizar Senha", use_container_width=True):
            if n_senha:
                supabase.table("usuarios").update({"senha": n_senha}).eq("id", dados_user['id']).execute()
                st.success("Senha alterada!")

    if nivel == "ADMIN":
        st.divider()
        st.subheader("🛠️ Gestão de Usuários (ADMIN)")
        todos = supabase.table("usuarios").select("*").execute().data
        if todos:
            sel = st.selectbox("Selecionar Colaborador", [u['nome'] for u in todos])
            target = next(u for u in todos if u['nome'] == sel)
            
            e_pref = st.text_input("Editar Prefixo", value=target.get('email','').split('@')[0])
            e_tel = st.text_input("Editar Telefone", value=target.get('telefone',''))
            e_senha = st.text_input("Resetar Senha", type="password")

            if st.button(f"Salvar Alterações em {sel}", use_container_width=True):
                email_f = f"{e_pref.strip().lower()}@grupoacelerador.com.br"
                
                # Valida se o e-mail novo já existe em OUTRO usuário
                dup = supabase.table("usuarios").select("id").eq("email", email_f).neq("id", target['id']).execute()
                
                if len(dup.data) > 0:
                    st.error("❌ Este e-mail já está em uso por outro colaborador.")
                else:
                    upd = {"email": email_f, "telefone": formatar_telefone(e_tel)}
                    if e_senha: upd["senha"] = e_senha
                    supabase.table("usuarios").update(upd).eq("id", target['id']).execute()
                    st.success("Dados atualizados!")
                    st.rerun()