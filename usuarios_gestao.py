import streamlit as st
import pandas as pd
import hashlib
from database import supabase, registrar_auditoria

def hash_password(password):
    """Gera o hash para que a nova senha funcione no login."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def render_usuario_gestao():
    # Segurança: Acesso restrito a administradores e gestores
    nivel_logado = st.session_state.get('nivel', '')
    if nivel_logado not in ["ADMIN", "GESTAO"]:
        st.error("Acesso restrito a administradores e gestores.")
        st.stop()
        return

    st.title("🛠️ Gestão de Equipe")
    st.markdown("Visualize, edite níveis, departamentos ou bloqueie acessos.")

    # --- DEFINIÇÃO DE OPÇÕES ---
    OPCOES_NIVEL = ["USUARIO", "GESTAO", "ADMIN", "AUDITOR"]
    OPCOES_DEPARTAMENTO = ["SDR", "Especialista", "Venda de Ingresso","Auditor"]

    try:
        # 1. Busca TODOS os usuários ativos e inativos
        res = supabase.table("usuarios").select("*").order("nome").execute()
        lista_usuarios = res.data
        
        if lista_usuarios:
            # 2. TABELA DE VISUALIZAÇÃO COM ESTILIZAÇÃO
            df = pd.DataFrame(lista_usuarios)
            
            # Tratamento caso a coluna departamento não exista no banco ainda
            if 'departamento' not in df.columns:
                df['departamento'] = "SDR"
            else:
                df['departamento'] = df['departamento'].fillna("SDR")
                
            df_view = df[['nome', 'user', 'telefone', 'nivel', 'departamento', 'esta_ativo']].copy()
            
            # Formatação visual para o Status
            df_view['esta_ativo'] = df_view['esta_ativo'].map({True: "✅ Ativo", False: "🚫 Bloqueado"})
            df_view.columns = ['Nome Completo', 'E-mail/Login', 'WhatsApp', 'Nível', 'Departamento', 'Status']
            
            st.dataframe(df_view, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("⚙️ Editar Colaborador")

            # 3. SELECTBOX PARA ESCOLHER O USUÁRIO
            opcoes = {f"{u['nome']} ({u['user']})": u for u in lista_usuarios}
            escolha = st.selectbox("Selecione o Colaborador para alterar:", [""] + list(opcoes.keys()))

            if escolha:
                user_data = opcoes[escolha]
                
                # Tratamento do departamento atual do usuário selecionado
                dept_atual = user_data.get('departamento')
                if not dept_atual or dept_atual not in OPCOES_DEPARTAMENTO:
                    dept_atual = "SDR"
                    
                # Tratamento do nivel atual (Agora usando USUARIO como padrão)
                nivel_atual = user_data.get('nivel')
                if not nivel_atual or nivel_atual not in OPCOES_NIVEL:
                    nivel_atual = "USUARIO"

                # Formulário de edição
                with st.form(f"form_edit_{user_data['user']}", border=True):
                    col1, col2 = st.columns(2)
                    novo_nome = col1.text_input("Nome", value=user_data.get('nome'))
                    novo_tel = col2.text_input("Telefone", value=user_data.get('telefone'))
                    
                    # --- NOVOS CAMPOS: NÍVEL E DEPARTAMENTO ---
                    col_nivel, col_dept = st.columns(2)
                    novo_nivel = col_nivel.selectbox("Nível de Acesso", OPCOES_NIVEL, index=OPCOES_NIVEL.index(nivel_atual))
                    novo_dept = col_dept.selectbox("Departamento", OPCOES_DEPARTAMENTO, index=OPCOES_DEPARTAMENTO.index(dept_atual))
                    
                    col3, col4 = st.columns(2)
                    reset_senha = col3.text_input("Resetar Senha (Opcional)", type="password", help="Deixe vazio para não alterar")
                    status_ativo = col4.toggle("Conta Ativa (Acesso liberado)", value=user_data.get('esta_ativo', True))

                    if st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary"):
                        if not novo_nome:
                            st.warning("O nome não pode estar vazio.")
                        else:
                            # --- LÓGICA DE AUDITORIA: COMPARAÇÃO ANTES/DEPOIS ---
                            mudancas = []
                            
                            nome_limpo = novo_nome.strip()
                            if user_data.get('nome') != nome_limpo:
                                mudancas.append(f"Nome: '{user_data.get('nome')}' ➡️ '{nome_limpo}'")
                            
                            tel_antigo = user_data.get('telefone') or "Vazio"
                            tel_novo = novo_tel.strip() if novo_tel else "Vazio"
                            if tel_antigo != tel_novo:
                                mudancas.append(f"Telefone: '{tel_antigo}' ➡️ '{tel_novo}'")
                                
                            if nivel_atual != novo_nivel:
                                mudancas.append(f"Nível: '{nivel_atual}' ➡️ '{novo_nivel}'")
                                
                            if dept_atual != novo_dept:
                                mudancas.append(f"Depto: '{dept_atual}' ➡️ '{novo_dept}'")
                                
                            if user_data.get('esta_ativo', True) != status_ativo:
                                status_antigo = "Ativo" if user_data.get('esta_ativo', True) else "Bloqueado"
                                status_novo = "Ativo" if status_ativo else "Bloqueado"
                                mudancas.append(f"Status: '{status_antigo}' ➡️ '{status_novo}'")
                                
                            if reset_senha:
                                mudancas.append("Senha: Resetada")

                            # Se não houve nenhuma mudança, avisa e nem faz update
                            if not mudancas:
                                st.info("Nenhuma alteração foi detectada.")
                            else:
                                # Prepara os dados para salvar
                                payload = {
                                    "nome": nome_limpo, 
                                    "telefone": tel_novo if tel_novo != "Vazio" else None, 
                                    "nivel": novo_nivel,
                                    "departamento": novo_dept,
                                    "esta_ativo": status_ativo
                                }
                                
                                if reset_senha:
                                    payload["senha"] = hash_password(reset_senha)
                                
                                # Monta o texto bonito para o Log
                                detalhes_log = "Alterações realizadas:\n" + " | ".join(mudancas)
                                
                                try:
                                    # 1. Atualiza no Banco
                                    supabase.table("usuarios").update(payload).eq("user", user_data['user']).execute()
                                    
                                    # 2. Registra Auditoria com o Antes e Depois
                                    # (Como atualizamos o database.py, agora podemos enviar o colaborador_afetado)
                                    registrar_auditoria(
                                        acao="ALTERAÇÃO DE USUÁRIO",
                                        detalhes=detalhes_log,
                                        colaborador_afetado=nome_limpo
                                    )
                                    
                                    st.success(f"Dados de {nome_limpo} atualizados com sucesso!")
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Erro ao salvar alterações: {e}")
        else:
            st.info("Nenhum usuário cadastrado no sistema.")

    except Exception as e:
        st.error(f"Erro ao carregar lista: {e}")