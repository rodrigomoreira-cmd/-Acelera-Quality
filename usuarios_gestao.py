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

    # --- VISÃO DO MEU PERFIL ---
    st.subheader("Meus Dados")
    
    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            st.text_input("Nome", value=dados_user['nome'], disabled=True)
            st.text_input("Usuário de Acesso", value=dados_user['user'], disabled=True)
            
        with col2:
            # Alinhamento manual do rótulo do e-mail
            st.markdown("<p style='margin-bottom: -35px;'>E-mail Institucional</p>", unsafe_allow_html=True)
            c_prefixo, c_dominio = st.columns([1.5, 1])
            
            p_disabled = False if nivel == "ADMIN" else True
            
            with c_prefixo:
                novo_prefixo_meu = st.text_input(
                    "Prefixo", 
                    value=prefixo_atual, 
                    disabled=p_disabled, 
                    label_visibility="collapsed",
                    key="meu_prefixo_input"
                )
            with c_dominio:
                # Alinhamento da caixa de info com o input
                st.info("@grupoacelerador.com.br")
                
            st.text_input("Telefone", value=dados_user.get('telefone', ''), disabled=p_disabled)

    # BOTÃO ALTERAR SENHA
    with st.expander("🔐 Alterar Minha Senha"):
        nova_senha = st.text_input("Nova Senha", type="password")
        confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
        
        if st.button("Atualizar Senha", use_container_width=True):
            if nova_senha == confirma_senha and nova_senha != "":
                try:
                    supabase.table("usuarios").update({"senha": nova_senha}).eq("id", dados_user['id']).execute()
                    st.success("✅ Senha alterada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao atualizar senha: {e}")
            else:
                st.error("❌ As senhas não coincidem ou campo vazio.")

    st.divider()

    # --- VISÃO EXCLUSIVA DO ADMIN (GESTÃO DE OUTROS USUÁRIOS) ---
    if nivel == "ADMIN":
        st.subheader("🛠️ Painel de Controle de Usuários (ADMIN)")
        
        todos_users = supabase.table("usuarios").select("*").execute()
        df_users = todos_users.data

        if df_users:
            nomes_colaboradores = [u['nome'] for u in df_users]
            sdr_para_editar = st.selectbox("Selecione o Colaborador", nomes_colaboradores)

            target = next(item for item in df_users if item["nome"] == sdr_para_editar)
            prefixo_target = target.get('email', '').split('@')[0]

            col_edit1, col_edit2 = st.columns([1.5, 1])
            
            with col_edit1:
                edit_prefixo = st.text_input("Editar Prefixo do E-mail", value=prefixo_target)
            with col_edit2:
                st.markdown("<br>", unsafe_allow_html=True)
                st.info("@grupoacelerador.com.br")

            edit_tel_raw = st.text_input("Editar Telefone", value=target.get('telefone', ''))
            edit_senha = st.text_input("Resetar Senha (Opcional)", placeholder="Deixe vazio para manter a atual", type="password")

            if st.button(f"Salvar Alterações em {sdr_para_editar}", use_container_width=True):
                if not validar_prefixo(edit_prefixo):
                    st.error("❌ Prefixo inválido! Não use espaços ou símbolos especiais.")
                else:
                    email_final = f"{edit_prefixo.strip().lower()}@grupoacelerador.com.br"
                    tel_formatado = formatar_telefone(edit_tel_raw)
                    
                    updates = {
                        "email": email_final,
                        "telefone": tel_formatado
                    }
                    if edit_senha:
                        updates["senha"] = edit_senha
                    
                    try:
                        supabase.table("usuarios").update(updates).eq("id", target['id']).execute()
                        st.success(f"✅ Dados de {sdr_para_editar} atualizados!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao atualizar: {e}")