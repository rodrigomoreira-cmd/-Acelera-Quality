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
            opcoes_nivel = ["USUARIO"]
            st.info("💡 Como Gestor, você possui permissão para cadastrar apenas perfis operacionais (Usuários).")
        elif nivel_logado == "GERENCIA":
            opcoes_nivel = ["USUARIO", "GESTAO"]
            st.info("💡 Como Gerência, pode cadastrar Usuários e Gestores.")
        else:
            opcoes_nivel = ["USUARIO", "GESTAO", "GERENCIA", "AUDITOR", "ADMIN"]
        
        nivel_acesso = col5.selectbox("Nível de Permissão", options=opcoes_nivel, index=0)
        
        # --- SELEÇÃO DE DEPARTAMENTO E GESTOR ---
        opcoes_departamento = ["SDR", "Especialista", "Venda de Ingresso", "Auditor"]
        departamento = col6.selectbox("Departamento da Equipe", options=opcoes_departamento, index=0)

        # --- NOVO: BUSCA OS GESTORES ATIVOS NO BANCO ---
        st.divider()
        st.markdown("#### 🎯 Alocação de Equipe")
        
        # Se for um usuário comum, precisamos dizer quem é o chefe dele
        if nivel_acesso == "USUARIO":
            try:
                # Busca quem tem nível GESTAO
                res_gestores = supabase.table("usuarios").select("nome").eq("nivel", "GESTAO").execute()
                lista_gestores = ["Sem Gestor"] + [g['nome'] for g in res_gestores.data]
            except Exception:
                lista_gestores = ["Sem Gestor"]
                
            # Se for um gestor criando a conta, já fixa o nome dele
            if nivel_logado == "GESTAO":
                gestor_escolhido = st.selectbox("Gestor Responsável", [admin_logado])
            else:
                gestor_escolhido = st.selectbox("Selecione o Gestor Responsável", lista_gestores)
        else:
            gestor_escolhido = None
            st.caption("Apenas o nível 'USUARIO' precisa ser alocado a um Gestor específico.")

        st.divider()
        
        if st.form_submit_button("🚀 Finalizar Cadastro", type="primary"):
            if not nome_completo or not user_prefix or not senha_pura:
                st.error("⚠️ Preencha os campos obrigatórios (Nome, Usuário e Senha).")
            else:
                try:
                    email_completo = f"{user_prefix.strip().lower()}@grupoacelerador.com.br"
                    
                    check = supabase.table("usuarios").select("user").eq("user", email_completo).execute()
                    
                    if check.data:
                        st.error(f"❌ O usuário '{email_completo}' já existe.")
                    else:
                        senha_hash = hash_password(senha_pura)

                        payload = {
                            "nome": nome_completo.strip(),
                            "user": email_completo,
                            "email": email_completo,
                            "senha": senha_hash,
                            "telefone": telefone.strip() if telefone else None,
                            "nivel": nivel_acesso,
                            "departamento": departamento,
                            "gestor_responsavel": gestor_escolhido if gestor_escolhido != "Sem Gestor" else None,
                            "esta_ativo": True
                        }
                        
                        supabase.table("usuarios").insert(payload).execute()

                        registrar_auditoria(
                            acao="CADASTRO DE USUÁRIO",
                            colaborador_afetado=nome_completo.strip(),
                            detalhes=f"Criou '{email_completo}' | Nível: '{nivel_acesso}' | Dept: '{departamento}' | Gestor: '{gestor_escolhido}'."
                        )
                        
                        st.success(f"✅ {nome_completo.strip()} cadastrado com sucesso!")
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro ao cadastrar: {e}")