import streamlit as st
from database import supabase

def render_cadastro():
    st.title("👥 Cadastro de Novo Usuário")
    st.markdown("O e-mail será gerado automaticamente com o domínio **@grupoacelerador.com.br**.")

    with st.form("form_cadastro_final", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome_completo = col1.text_input("Nome Completo", placeholder="Ex: João Silva")
        user_prefix = col2.text_input("Usuário (Apenas o prefixo)", placeholder="Ex: joao.silva")
        
        col3, col4 = st.columns(2)
        senha = col3.text_input("Senha Inicial", type="password")
        # --- ADIÇÃO DO CAMPO TELEFONE ---
        telefone = col4.text_input("Telefone/WhatsApp", placeholder="(11) 99999-9999")

        col5, col_extra = st.columns(2)
        nivel_acesso = col5.selectbox("Nível de Permissão", options=["SDR", "ADMIN"], index=0)

        st.divider()
        
        if st.form_submit_button("🚀 Finalizar Cadastro"):
            if not nome_completo or not user_prefix or not senha:
                st.error("⚠️ Preencha os campos obrigatórios (Nome, Usuário e Senha).")
            else:
                try:
                    email_completo = f"{user_prefix.strip().lower()}@grupoacelerador.com.br"
                    
                    # Verifica duplicidade no banco
                    check = supabase.table("usuarios").select("user").eq("user", email_completo).execute()
                    
                    if check.data:
                        st.error(f"❌ O usuário '{email_completo}' já existe.")
                    else:
                        # Payload de Cadastro do Usuário
                        payload = {
                            "nome": nome_completo.strip(),
                            "user": email_completo,
                            "email": email_completo,
                            "senha": senha,
                            "telefone": telefone.strip() if telefone else None, # Envia o telefone
                            "nivel": nivel_acesso,
                            "esta_ativo": True
                        }
                        
                        supabase.table("usuarios").insert(payload).execute()

                        # REGISTRO AUTOMÁTICO NA AUDITORIA
                        auditoria_data = {
                            "admin_responsavel": st.session_state.get('user_nome'),
                            "colaborador_afetado": nome_completo.strip(),
                            "acao": "CADASTRO",
                            "detalhes": f"Criou o usuário {email_completo} com nível {nivel_acesso} e telefone {telefone}."
                        }
                        supabase.table("auditoria").insert(auditoria_data).execute()
                        
                        st.success(f"✅ {nome_completo} cadastrado com sucesso!")
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro ao cadastrar: {e}")