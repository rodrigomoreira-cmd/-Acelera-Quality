import streamlit as st
import pandas as pd
import hashlib
from database import supabase, registrar_auditoria

def hash_password(password):
    """Gera o hash para que a nova senha funcione no login."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def render_usuario_gestao():
    # Segurança: Acesso restrito a administradores
    if st.session_state.get('nivel') != "ADMIN":
        st.error("Acesso restrito a administradores.")
        return

    st.title("🛠️ Gestão de Equipe (SDRs)")
    st.markdown("Visualize, edite ou bloqueie o acesso de colaboradores.")

    try:
        # 1. Busca APENAS os SDRs
        res = supabase.table("usuarios").select("*").eq("nivel", "SDR").order("nome").execute()
        lista_sdrs = res.data
        
        if lista_sdrs:
            # 2. TABELA DE VISUALIZAÇÃO COM ESTILIZAÇÃO
            df = pd.DataFrame(lista_sdrs)
            df_view = df[['nome', 'user', 'telefone', 'esta_ativo']].copy()
            
            # Formatação visual para o Status
            df_view['esta_ativo'] = df_view['esta_ativo'].map({True: "✅ Ativo", False: "🚫 Bloqueado"})
            df_view.columns = ['Nome Completo', 'E-mail/Login', 'WhatsApp', 'Status']
            
            st.dataframe(df_view, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("⚙️ Editar Colaborador")

            # 3. SELECTBOX PARA ESCOLHER O SDR
            opcoes = {f"{u['nome']} ({u['user']})": u for u in lista_sdrs}
            escolha = st.selectbox("Selecione o SDR para alterar:", [""] + list(opcoes.keys()))

            if escolha:
                user_data = opcoes[escolha]
                
                # Formulário de edição
                with st.form(f"form_edit_{user_data['user']}", border=True):
                    col1, col2 = st.columns(2)
                    novo_nome = col1.text_input("Nome", value=user_data.get('nome'))
                    novo_tel = col2.text_input("Telefone", value=user_data.get('telefone'))
                    
                    col3, col4 = st.columns(2)
                    reset_senha = col3.text_input("Resetar Senha (Opcional)", type="password", help="Deixe vazio para não alterar")
                    status_ativo = col4.toggle("Conta Ativa (Acesso liberado)", value=user_data.get('esta_ativo', True))

                    if st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary"):
                        if not novo_nome:
                            st.warning("O nome não pode estar vazio.")
                        else:
                            payload = {
                                "nome": novo_nome.strip(), 
                                "telefone": novo_tel.strip() if novo_tel else None, 
                                "esta_ativo": status_ativo
                            }
                            
                            # CRIPTOGRAFIA NO RESET DE SENHA
                            detalhes_log = f"Status: {'Ativo' if status_ativo else 'Bloqueado'}."
                            if reset_senha:
                                payload["senha"] = hash_password(reset_senha)
                                detalhes_log += " Senha resetada pelo administrador."
                            
                            try:
                                # 1. Atualiza no Banco
                                supabase.table("usuarios").update(payload).eq("user", user_data['user']).execute()
                                
                                # 2. Registra Auditoria
                                registrar_auditoria(
                                    acao="ALTERAÇÃO DE USUÁRIO",
                                    colaborador_afetado=novo_nome,
                                    detalhes=detalhes_log
                                )
                                
                                st.success(f"Dados de {novo_nome} atualizados!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Erro ao salvar alterações: {e}")
        else:
            st.info("Nenhum SDR cadastrado no sistema.")

    except Exception as e:
        st.error(f"Erro ao carregar lista: {e}")