import streamlit as st
from database import supabase
import time # Import necessário para o contador de tempo

def render_recuperacao():
    st.subheader("🔑 Recuperar Acesso")
    st.markdown("Confirme seus dados para redefinir a senha.")

    # Inicializa o passo do formulário se não existir
    if 'passo_recuperacao' not in st.session_state:
        st.session_state.passo_recuperacao = 1

    # PASSO 1: VALIDAÇÃO DE IDENTIDADE
    if st.session_state.passo_recuperacao == 1:
        user_input = st.text_input("Usuário de Acesso", key="rec_user_input")
        email_input = st.text_input("E-mail Institucional", key="rec_email_input")

        if st.button("Validar Dados", use_container_width=True):
            if not user_input or not email_input:
                st.warning("⚠️ Preencha os campos para validar.")
            else:
                res = supabase.table("usuarios").select("*").eq("user", user_input.strip().lower()).eq("email", email_input.strip().lower()).execute()
                
                if res.data:
                    st.session_state.user_recuperacao = res.data[0]
                    st.session_state.passo_recuperacao = 2
                    st.rerun()
                else:
                    st.error("❌ Dados não encontrados no sistema. Verifique as informações.")

    # PASSO 2: DEFINIÇÃO DA NOVA SENHA
    elif st.session_state.passo_recuperacao == 2:
        st.info(f"Dados validados para: **{st.session_state.user_recuperacao['nome']}**")
        
        nova_p = st.text_input("Digite a Nova Senha", type="password", key="new_pass_final")
        conf_p = st.text_input("Confirme a Nova Senha", type="password", key="conf_pass_final")

        if st.button("Redefinir Senha", use_container_width=True, type="primary"):
            if nova_p and nova_p == conf_p:
                try:
                    # Atualiza a senha no banco de dados
                    supabase.table("usuarios").update({"senha": nova_p}).eq("id", st.session_state.user_recuperacao['id']).execute()
                    
                    # Registra no Log de Auditoria
                    from usuarios_gestao import registrar_log
                    registrar_log(
                        "SISTEMA", 
                        st.session_state.user_recuperacao['nome'], 
                        "Recuperação de Senha", 
                        "Senha redefinida com sucesso pelo usuário via tela de recuperação."
                    )
                    
                    # MENSAGEM E REDIRECIONAMENTO AUTOMÁTICO
                    st.success("✅ Senha alterada com sucesso! Redirecionando para a tela de login em 3 segundos...")
                    
                    # Limpa os estados temporários de recuperação antes de voltar
                    st.session_state.auth_mode = "login"
                    st.session_state.passo_recuperacao = 1
                    if 'user_recuperacao' in st.session_state:
                        del st.session_state.user_recuperacao
                    
                    # Aguarda 3 segundos
                    time.sleep(3)
                    
                    # Força a atualização da página para o Login
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao salvar nova senha: {e}")
            else:
                st.error("❌ As senhas não coincidem ou estão vazias.")

    # Botão para cancelar e voltar ao login a qualquer momento
    if st.button("Cancelar e Voltar"):
        st.session_state.auth_mode = "login"
        st.session_state.passo_recuperacao = 1
        st.rerun()