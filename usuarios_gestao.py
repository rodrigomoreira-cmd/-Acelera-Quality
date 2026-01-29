import streamlit as st
from database import supabase

def render_usuario_gestao():
    # 1. Identificação do usuário logado
    nivel_logado = str(st.session_state.get('nivel', 'SDR')).upper()
    login_proprio = st.session_state.get('user_login', '')
    nome_proprio = st.session_state.get('user_nome', 'Usuário')

    st.title("👤 Gestão de Perfil e Usuários")

    # --- BUSCA DADOS ATUALIZADOS DO PRÓPRIO USUÁRIO (Incluindo telefone) ---
    try:
        res_me = supabase.table("usuarios").select("*").eq("user", login_proprio).execute()
        meus_dados = res_me.data[0] if res_me.data else {}
    except:
        meus_dados = {}

    # --- SEÇÃO 1: MEU PERFIL (Visível para todos) ---
    with st.container(border=True):
        st.subheader("Meus Dados")
        c1, c2, c3, c4 = st.columns(4)
        c1.write(f"**Nome:** {nome_proprio}")
        c2.write(f"**Login:** {login_proprio}")
        c3.write(f"**Nível:** {nivel_logado}")
        c4.write(f"**Telefone:** {meus_dados.get('telefone', 'Não informado')}")

    with st.expander("🔐 Alterar Minha Senha"):
        with st.form("form_minha_senha"):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirmar = st.text_input("Confirme a Nova Senha", type="password")
            if st.form_submit_button("Atualizar Minha Senha"):
                if nova_senha == confirmar and len(nova_senha) >= 4:
                    try:
                        supabase.table("usuarios").update({"senha": nova_senha}).eq("user", login_proprio).execute()
                        st.success("Sua senha foi atualizada!")
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")
                else:
                    st.error("Senhas não coincidem ou são muito curtas.")

    # --- SEÇÃO 2: PAINEL ADMINISTRATIVO (Apenas para ADM) ---
    if nivel_logado == "ADMIN":
        st.divider()
        st.header("🛠️ Painel Administrativo")
        st.markdown("Gerencie o acesso e as informações de todos os colaboradores.")

        try:
            # Busca todos os usuários cadastrados
            res = supabase.table("usuarios").select("*").order("nome").execute()
            lista_usuarios = res.data
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")
            return

        if lista_usuarios:
            # Seletor de usuário para edição
            dict_usuarios = {f"{u['nome']} ({u['user']})": u for u in lista_usuarios}
            selecionado = st.selectbox("Selecione um colaborador para editar:", [""] + list(dict_usuarios.keys()))

            if selecionado:
                user_data = dict_usuarios[selecionado]
                
                with st.form(f"form_edit_adm_{user_data['user']}"):
                    st.subheader(f"Gerenciar Acesso: {user_data['user']}")
                    
                    col_ed1, col_ed2, col_ed3 = st.columns(3)
                    
                    # Nome pode ser corrigido
                    novo_nome = col_ed1.text_input("Nome de Cadastro", value=user_data.get('nome', ''))
                    
                    # --- ADIÇÃO DO CAMPO TELEFONE NA EDIÇÃO ---
                    novo_telefone = col_ed2.text_input("Telefone/WhatsApp", value=user_data.get('telefone', ''))
                    
                    # NÍVEL DE PERMISSÃO DESABILITADO
                    nivel_atual = user_data.get('nivel', 'SDR')
                    col_ed3.text_input("Nível de Permissão (Fixo)", value=nivel_atual, disabled=True)
                    
                    st.divider()
                    
                    col_op1, col_op2 = st.columns(2)
                    with col_op1:
                        reset_senha = st.text_input("Resetar Senha", type="password", placeholder="Deixe em branco para manter")
                    
                    with col_op2:
                        status_db = user_data.get('esta_ativo', True)
                        ativar_user = st.toggle("Acesso Habilitado", value=status_db)
                        st.caption("🟢 Ativo" if ativar_user else "🔴 Bloqueado")

                    if st.form_submit_button("💾 Salvar Alterações"):
                        update_payload = {
                            "nome": novo_nome,
                            "telefone": novo_telefone,
                            "esta_ativo": ativar_user
                        }
                        
                        if reset_senha:
                            update_payload["senha"] = reset_senha
                        
                        try:
                            # 1. Atualiza o usuário
                            supabase.table("usuarios").update(update_payload).eq("user", user_data['user']).execute()
                            
                            # 2. REGISTRA NA AUDITORIA
                            detalhes_log = f"Editou dados (Telefone: {novo_telefone}, Ativo: {ativar_user})."
                            if reset_senha:
                                detalhes_log += " Senha foi resetada."
                            
                            auditoria_payload = {
                                "admin_responsavel": nome_proprio,
                                "colaborador_afetado": user_data.get('nome'),
                                "acao": "ALTERAÇÃO DE USUÁRIO",
                                "detalhes": detalhes_log
                            }
                            supabase.table("auditoria").insert(auditoria_payload).execute()
                            
                            st.success(f"Alterações para {user_data['nome']} salvas com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")