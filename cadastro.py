import streamlit as st
import time
from database import supabase

def render_cadastro():
    # 1. Verificação de Permissão: Apenas ADMIN e GESTAO podem acessar
    nivel_logado = st.session_state.get('nivel', '').upper()
    
    if nivel_logado not in ["ADMIN", "GESTAO"]:
        st.error("⛔ Você não tem permissão para acessar esta página.")
        return

    st.title("👥 Cadastro de Novo Usuário")
    st.markdown("O e-mail será gerado automaticamente com o domínio **@grupoacelerador.com.br**.")

    # Container para organizar o visual
    with st.container(border=True):
        with st.form("form_cadastro_final", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_completo = st.text_input("Nome Completo", placeholder="Ex: João Silva")
                user_prefix = st.text_input("Usuário (Apenas o prefixo)", placeholder="Ex: joao.silva").strip().lower()
            
            with col2:
                # ADICIONADO: Opção GESTAO na lista
                opcoes_nivel = ["SDR", "GESTAO", "ADMIN"]
                nivel_acesso = st.selectbox("Nível de Permissão", options=opcoes_nivel, index=0)
                
                senha_pura = st.text_input("Senha Inicial", type="password")
            
            # Campo opcional de Foto
            foto_url = st.text_input("URL da Foto (Opcional):", placeholder="https://...")

            st.divider()
            
            col_b1, col_b2 = st.columns([1, 2])
            enviar = col_b2.form_submit_button("🚀 Finalizar Cadastro", type="primary", use_container_width=True)

            if enviar:
                # 2. Validação de campos obrigatórios
                if not nome_completo or not user_prefix or not senha_pura:
                    st.warning("⚠️ Preencha os campos obrigatórios (Nome, Usuário e Senha).")
                elif len(senha_pura) < 4:
                    st.warning("⚠️ A senha deve ter pelo menos 4 caracteres.")
                else:
                    try:
                        # Monta o e-mail final
                        email_completo = f"{user_prefix}@grupoacelerador.com.br"
                        
                        # 3. Verifica duplicidade no banco
                        check = supabase.table("usuarios").select("user").eq("user", email_completo).execute()
                        
                        if check.data:
                            st.error(f"❌ O usuário '{email_completo}' já existe no sistema.")
                        else:
                            # 4. Preparação do Cadastro
                            # Nota: Enviando senha pura para manter compatibilidade com auth.py atual
                            payload = {
                                "nome": nome_completo.strip(),
                                "user": email_completo,
                                "email": email_completo, # Redundância útil
                                "senha": senha_pura, 
                                "nivel": nivel_acesso,
                                "foto_url": foto_url if foto_url else None,
                                "esta_ativo": True
                            }
                            
                            # 5. Insere no Supabase
                            supabase.table("usuarios").insert(payload).execute()

                            # Mensagem de Sucesso
                            st.success(f"✅ Usuário criado com sucesso!")
                            st.info(f"Login: **{email_completo}** | Nível: **{nivel_acesso}**")
                            time.sleep(2)
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Ocorreu um erro ao cadastrar: {e}")