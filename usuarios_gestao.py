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

def render_usuario_gestao():
    st.title("👤 Gerenciamento de Perfil")
    
    user_logado = st.session_state.user
    nivel = st.session_state.get('nivel', 'sdr').upper()

    # 1. BUSCA DADOS DO USUÁRIO NO BANCO
    res = supabase.table("usuarios").select("*").eq("nome", user_logado).execute()
    
    if not res.data:
        st.error("Erro ao carregar dados do perfil.")
        return

    dados_user = res.data[0]
    email_atual = dados_user.get('email', '')
    prefixo_atual = email_atual.split('@')[0] if '@' in email_atual else email_atual

    # --- SEÇÃO: MEUS DADOS (SDR e ADMIN) ---
    st.subheader("Meus Dados Pessoais")
    
    with st.container():
        # Campos empilhados verticalmente
        st.text_input("Nome Completo", value=dados_user['nome'], disabled=True)
        st.text_input("Usuário de Login", value=dados_user['user'], disabled=True)
        
        # Bloco de E-mail Institucional
        st.write("**E-mail Institucional**")
        col_pref, col_dom = st.columns([2, 1])
        
        # Apenas Admin pode editar o próprio prefixo; SDR apenas visualiza
        p_disabled = False if nivel == "ADMIN" else True
        
        with col_pref:
            novo_prefixo_meu = st.text_input(
                "Prefixo", 
                value=prefixo_atual, 
                disabled=p_disabled, 
                label_visibility="collapsed",
                key="meu_prefixo_input"
            )
        with col_dom:
            st.info("@grupoacelerador.com.br")
            
        st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=p_disabled)

    # BOTÃO ALTERAR SENHA (Disponível para todos)
    with st.expander("🔐 Alterar Minha Senha"):
        nova_senha = st.text_input("Nova Senha", type="password")
        confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
        
        if st.button("Atualizar Minha Senha", use_container_width=True):
            if nova_senha == confirma_senha and nova_senha != "":
                try:
                    supabase.table("usuarios").update({"senha": nova_senha}).eq("id", dados_user['id']).execute()
                    st.success("✅ Senha alterada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")
            else:
                st.error("❌ As senhas não coincidem ou campo está vazio.")

    st.divider()

    # --- SEÇÃO: GESTÃO DE USUÁRIOS (EXCLUSIVO ADMIN) ---
    if nivel == "ADMIN":
        st.subheader("🛠️ Painel de Controle de Usuários")
        
        todos_users = supabase.table("usuarios").select("*").execute()
        df_users = todos_users.data

        if df_users:
            nomes_colaboradores = [u['nome'] for u in df_users]
            sdr_para_editar = st.selectbox("Selecione o Colaborador para gerenciar", nomes_colaboradores)

            # Localiza os dados do usuário selecionado no menu
            target = next(item for item in df_users if item["nome"] == sdr_para_editar)
            prefixo_target = target.get('email', '').split('@')[0]

            # Campos de edição organizados verticalmente
            st.write(f"**Editando: {sdr_para_editar}**")
            
            st.write("Novo Prefixo de E-mail")
            col_ed_p, col_ed_d = st.columns([2, 1])
            with col_ed_p:
                edit_prefixo = st.text_input("E-mail Prefixo", value=prefixo_target, label_visibility="collapsed")
            with col_ed_d:
                st.info("@grupoacelerador.com.br")

            edit_tel_raw = st.text_input("Novo Telefone", value=target.get('telefone', ''))
            edit_senha = st.text_input("Resetar Senha (Opcional)", placeholder="Digite a nova senha se desejar alterar", type="password")

            if st.button(f"Confirmar Alterações em {sdr_para_editar}", use_container_width=True):
                # Validação de Segurança
                if not validar_prefixo(edit_prefixo):
                    st.error("❌ Prefixo inválido! Use apenas letras, números, '.' ou '_'.")
                else:
                    email_final = f"{edit_prefixo.strip().lower()}@grupoacelerador.com.br"
                    tel_formatado = formatar_telefone(edit_tel_raw)
                    
                    payload_update = {
                        "email": email_final,
                        "telefone": tel_formatado
                    }
                    if edit_senha:
                        payload_update["senha"] = edit_senha
                    
                    try:
                        supabase.table("usuarios").update(payload_update).eq("id", target['id']).execute()
                        st.success(f"✅ Dados de {sdr_para_editar} atualizados!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar alterações: {e}")