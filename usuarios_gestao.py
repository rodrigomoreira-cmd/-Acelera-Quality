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

def render_usuario_gestao():
    st.title("👤 Gerenciamento de Perfil")
    
    user_logado = st.session_state.user
    nivel = st.session_state.get('nivel', 'sdr').upper()
    res = supabase.table("usuarios").select("*").eq("nome", user_logado).execute()
    
    if not res.data:
        st.error("Erro ao carregar dados do perfil.")
        return

    dados_user = res.data[0]
    email_atual = dados_user.get('email', '')
    prefixo_atual = email_atual.split('@')[0] if '@' in email_atual else email_atual

    st.subheader("Meus Dados")
    
    # Campos empilhados verticalmente para facilitar a visualização
    st.text_input("Nome Completo", value=dados_user['nome'], disabled=True)
    st.text_input("Usuário de Login", value=dados_user['user'], disabled=True)

    # Organização do E-mail em bloco único
    st.write("**E-mail Institucional**")
    col_p, col_d = st.columns([2, 1])
    p_disabled = False if nivel == "ADMIN" else True
    
    with col_p:
        novo_pref = st.text_input("Prefixo", value=prefixo_atual, disabled=p_disabled, label_visibility="collapsed")
    with col_d:
        st.info("@grupoacelerador.com.br")
            
    st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=p_disabled)

    st.divider()

    # Seção de Senha
    with st.expander("🔐 Alterar Minha Senha"):
        n_senha = st.text_input("Nova Senha", type="password")
        c_senha = st.text_input("Confirme a Nova Senha", type="password")
        if st.button("Atualizar Minha Senha", use_container_width=True):
            if n_senha == c_senha and n_senha != "":
                supabase.table("usuarios").update({"senha": n_senha}).eq("id", dados_user['id']).execute()
                st.success("✅ Senha alterada com sucesso!")
            else:
                st.error("❌ As senhas não coincidem ou campo vazio.")

    # Painel Administrativo (Apenas para ADMIN)
    if nivel == "ADMIN":
        st.divider()
        st.subheader("🛠️ Painel de Gestão de Usuários")
        
        todos_users = supabase.table("usuarios").select("*").execute().data
        if todos_users:
            nomes = [u['nome'] for u in todos_users]
            selecionado = st.selectbox("Selecione um Colaborador para Editar", nomes)
            target = next(u for u in todos_users if u['nome'] == selecionado)
            
            t_prefixo = target.get('email', '').split('@')[0]
            
            # Campos de edição também empilhados
            edit_pref = st.text_input(f"Editar Prefixo E-mail ({selecionado})", value=t_prefixo)
            edit_tel = st.text_input(f"Editar Telefone ({selecionado})", value=target.get('telefone', ''))
            edit_senha = st.text_input("Resetar Senha (Opcional)", type="password", placeholder="Nova senha se desejar alterar")

            if st.button(f"Salvar Alterações em {selecionado}", use_container_width=True):
                if validar_prefixo(edit_pref):
                    email_f = f"{edit_pref.lower().strip()}@grupoacelerador.com.br"
                    updates = {"email": email_f, "telefone": formatar_telefone(edit_tel)}
                    if edit_senha: updates["senha"] = edit_senha
                    
                    supabase.table("usuarios").update(updates).eq("id", target['id']).execute()
                    st.success("✅ Alterações salvas!")
                    st.rerun()
                else:
                    st.error("❌ Prefixo inválido.")