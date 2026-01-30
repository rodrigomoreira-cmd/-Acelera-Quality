import streamlit as st
import hashlib # Necessário para a senha
from database import supabase, registrar_auditoria

def hash_password(password):
    """Transforma a senha em SHA-256 para manter o padrão do login."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def render_cadastro():
    st.title("👥 Cadastro de Novo Usuário")
    st.markdown("O e-mail será gerado automaticamente com o domínio **@grupoacelerador.com.br**.")

    # Usamos st.container para melhor visualização
    with st.form("form_cadastro_final", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome_completo = col1.text_input("Nome Completo", placeholder="Ex: João Silva")
        user_prefix = col2.text_input("Usuário (Apenas o prefixo)", placeholder="Ex: joao.silva")
        
        col3, col4 = st.columns(2)
        senha_pura = col3.text_input("Senha Inicial", type="password")
        telefone = col4.text_input("Telefone/WhatsApp", placeholder="(11) 99999-9999")

        col5, col_extra = st.columns(2)
        nivel_acesso = col5.selectbox("Nível de Permissão", options=["SDR", "ADMIN"], index=0)

        st.divider()
        
        if st.form_submit_button("🚀 Finalizar Cadastro"):
            # 1. Validação de campos obrigatórios
            if not nome_completo or not user_prefix or not senha_pura:
                st.error("⚠️ Preencha os campos obrigatórios (Nome, Usuário e Senha).")
            else:
                try:
                    # Limpeza e padronização
                    email_completo = f"{user_prefix.strip().lower()}@grupoacelerador.com.br"
                    
                    # 2. Verifica duplicidade no banco (coluna 'user')
                    check = supabase.table("usuarios").select("user").eq("user", email_completo).execute()
                    
                    if check.data:
                        st.error(f"❌ O usuário '{email_completo}' já existe.")
                    else:
                        # 3. CRIPTOGRAFIA DA SENHA (O ajuste que faltava)
                        senha_hash = hash_password(senha_pura)

                        # 4. Preparação do Cadastro
                        payload = {
                            "nome": nome_completo.strip(),
                            "user": email_completo,
                            "email": email_completo,
                            "senha": senha_hash, # Enviando o Hash, não a senha pura
                            "telefone": telefone.strip() if telefone else None,
                            "nivel": nivel_acesso,
                            "esta_ativo": True
                        }
                        
                        supabase.table("usuarios").insert(payload).execute()

                        # 5. Registro na Auditoria
                        registrar_auditoria(
                            acao="CADASTRO",
                            colaborador_afetado=nome_completo.strip(),
                            detalhes=f"Criou o usuário {email_completo} com nível {nivel_acesso}."
                        )
                        
                        st.success(f"✅ {nome_completo} cadastrado com sucesso!")
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro ao cadastrar: {e}")