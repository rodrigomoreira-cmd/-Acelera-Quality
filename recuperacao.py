import streamlit as st
import hashlib
import time
from database import supabase, registrar_auditoria

def hash_password(password):
    """Gera o hash SHA-256 para que a nova senha seja compatível com o login."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def render_recuperacao():
    st.subheader("🔑 Recuperar Acesso")
    st.markdown("Confirme seus dados cadastrados para redefinir sua senha.")

    # Inicializa o controle de passos
    if 'passo_recuperacao' not in st.session_state:
        st.session_state.passo_recuperacao = 1

    # PASSO 1: VALIDAÇÃO DE IDENTIDADE
    if st.session_state.passo_recuperacao == 1:
        with st.container(border=True):
            user_input = st.text_input("Usuário de Acesso (Login)", placeholder="ex: nome.sobrenome@domínio.com", key="rec_user_input")
            email_input = st.text_input("Confirme seu E-mail Institucional", key="rec_email_input")

            if st.button("Validar Meus Dados", use_container_width=True, type="primary"):
                if not user_input or not email_input:
                    st.warning("⚠️ Preencha ambos os campos para validar sua identidade.")
                else:
                    try:
                        # Busca o usuário que combine login E e-mail
                        res = supabase.table("usuarios").select("*")\
                            .eq("user", user_input.strip().lower())\
                            .eq("email", email_input.strip().lower())\
                            .execute()
                        
                        if res.data:
                            st.session_state.user_recuperacao = res.data[0]
                            st.session_state.passo_recuperacao = 2
                            st.rerun()
                        else:
                            st.error("❌ Dados não encontrados. Verifique se o login e e-mail estão corretos.")
                    except Exception as e:
                        st.error(f"Erro na validação: {e}")

    # PASSO 2: DEFINIÇÃO DA NOVA SENHA
    elif st.session_state.passo_recuperacao == 2:
        st.success(f"Identidade validada para: **{st.session_state.user_recuperacao['nome']}**")
        
        with st.container(border=True):
            nova_p = st.text_input("Crie uma Nova Senha", type="password", key="new_pass_final")
            conf_p = st.text_input("Confirme a Nova Senha", type="password", key="conf_pass_final")

            if st.button("Confirmar Redefinição", use_container_width=True, type="primary"):
                if nova_p and nova_p == conf_p:
                    if len(nova_p) < 6:
                        st.error("A senha deve ter no mínimo 6 caracteres.")
                    else:
                        try:
                            # 1. CRIPTOGRAFA A NOVA SENHA
                            senha_hash = hash_password(nova_p)

                            # 2. Atualiza no Banco de Dados
                            supabase.table("usuarios").update({"senha": senha_hash})\
                                .eq("id", st.session_state.user_recuperacao['id']).execute()
                            
                            # 3. Registra na Auditoria (Usando a função correta do database.py)
                            registrar_auditoria(
                                acao="RECUPERAÇÃO DE SENHA",
                                colaborador_afetado=st.session_state.user_recuperacao['nome'],
                                detalhes="O próprio usuário redefiniu a senha via módulo de recuperação."
                            )
                            
                            st.success("✅ Senha alterada! Você será levado ao login em instantes...")
                            
                            # Limpeza de sessão e redirecionamento
                            time.sleep(3)
                            st.session_state.auth_mode = "login"
                            st.session_state.passo_recuperacao = 1
                            if 'user_recuperacao' in st.session_state:
                                del st.session_state.user_recuperacao
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                else:
                    st.error("❌ As senhas não coincidem.")

    # Botão de retorno
    st.write("")
    if st.button("⬅️ Voltar para o Login", use_container_width=True):
        st.session_state.auth_mode = "login"
        st.session_state.passo_recuperacao = 1
        st.rerun()