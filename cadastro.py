import streamlit as st
import hashlib
from database import supabase, registrar_auditoria

def hash_password(password):
    """Transforma a senha em SHA-256 para manter o padrão do login."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def render_cadastro():
    st.title("👥 Cadastro de Novo Usuário")
    
    # Recupera o nível de quem está logado para aplicar a restrição
    nivel_logado = st.session_state.get('nivel', 'USUARIO').upper()
    admin_logado = st.session_state.get('user_nome', 'Admin')
    
    st.markdown("O e-mail será gerado automaticamente com o domínio **@grupoacelerador.com.br**.")

    with st.form("form_cadastro_final", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome_completo = col1.text_input("Nome Completo", placeholder="Ex: João Silva")
        user_prefix = col2.text_input("Usuário (Apenas o prefixo)", placeholder="Ex: joao.silva")
        
        col3, col4 = st.columns(2)
        senha_pura = col3.text_input("Senha Inicial", type="password")
        telefone = col4.text_input("Telefone/WhatsApp", placeholder="(11) 99999-9999")

        col5, col6 = st.columns(2)
        
        # --- LÓGICA DE RESTRIÇÃO DE NÍVEL ---
        if nivel_logado == "GESTAO":
            # Gestão só pode cadastrar perfil operacional (USUARIO)
            opcoes_nivel = ["USUARIO"]
            st.info("💡 Como Gestor, você possui permissão para cadastrar apenas perfis operacionais (Usuários).")
        else:
            # Admin pode cadastrar qualquer um
            opcoes_nivel = ["USUARIO", "GESTAO", "ADMIN", "AUDITOR"]
        
        nivel_acesso = col5.selectbox("Nível de Permissão", options=opcoes_nivel, index=0)
        
        # --- SELEÇÃO DE DEPARTAMENTO ---
        opcoes_departamento = ["SDR", "Especialista", "Venda de Ingresso","Auditor"]
        departamento = col6.selectbox("Departamento da Equipe", options=opcoes_departamento, index=0)

        st.divider()
        
        if st.form_submit_button("🚀 Finalizar Cadastro", type="primary"):
            # 1. Validação de campos obrigatórios
            if not nome_completo or not user_prefix or not senha_pura:
                st.error("⚠️ Preencha os campos obrigatórios (Nome, Usuário e Senha).")
            else:
                try:
                    # Limpeza e padronização
                    email_completo = f"{user_prefix.strip().lower()}@grupoacelerador.com.br"
                    
                    # 2. Verifica duplicidade no banco
                    check = supabase.table("usuarios").select("user").eq("user", email_completo).execute()
                    
                    if check.data:
                        st.error(f"❌ O usuário '{email_completo}' já existe.")
                    else:
                        # 3. Criptografia
                        senha_hash = hash_password(senha_pura)

                        # 4. Preparação do Cadastro
                        payload = {
                            "nome": nome_completo.strip(),
                            "user": email_completo,
                            "email": email_completo,
                            "senha": senha_hash,
                            "telefone": telefone.strip() if telefone else None,
                            "nivel": nivel_acesso,
                            "departamento": departamento,
                            "esta_ativo": True
                        }
                        
                        # Salva no banco de usuários
                        supabase.table("usuarios").insert(payload).execute()

                        # 5. --- 📸 LOG DE AUDITORIA ---
                        # Aqui usamos a câmera de segurança atualizada para gravar quem foi cadastrado
                        registrar_auditoria(
                            acao="CADASTRO DE USUÁRIO",
                            colaborador_afetado=nome_completo.strip(),
                            detalhes=f"Foi criado o login '{email_completo}' com o nível '{nivel_acesso}' para o departamento '{departamento}'."
                        )
                        
                        st.success(f"✅ {nome_completo.strip()} cadastrado com sucesso no time de {departamento}!")
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro ao cadastrar: {e}")