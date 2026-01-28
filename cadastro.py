import streamlit as st
import re
from database import supabase

def validar_prefixo(prefixo):
    """
    Permite apenas letras, números, pontos e sublinhados.
    Retorna True se for válido e False se houver espaços ou símbolos.
    """
    padrao = r'^[a-zA-Z0-9._]+$'
    return re.match(padrao, prefixo) is not None

def formatar_telefone(tel):
    """
    Remove caracteres não numéricos e aplica a máscara (XX) XXXXX-XXXX.
    """
    numeros = re.sub(r'\D', '', tel)
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return tel

def render_cadastro():
    st.title("👥 Cadastro de Novo Colaborador")
    st.markdown("Preencha as informações abaixo. Os campos estão organizados verticalmente para facilitar a leitura.")

    # Formulário com campos empilhados verticalmente
    with st.form("form_cadastro_vertical", clear_on_submit=True):
        
        # 1. Nome Completo
        nome = st.text_input("Nome Completo", placeholder="Digite o nome completo do colaborador")
        
        # 2. Usuário de Login
        usuario = st.text_input("Usuário de Login", placeholder="Ex: joao.silva (usado para entrar no sistema)")
        
        # 3. Bloco de E-mail Institucional
        st.write("**E-mail Institucional**")
        # Sub-colunas apenas para o prefixo e o domínio fixo ficarem na mesma linha
        col_pref, col_dom = st.columns([2, 1])
        with col_pref:
            prefixo_email = st.text_input("Prefixo do e-mail", placeholder="Ex: joao.silva", label_visibility="collapsed")
        with col_dom:
            st.info("@grupoacelerador.com.br")
            
        # 4. Telefone
        telefone_raw = st.text_input("Telefone de Contato", placeholder="Ex: 11999999999")
        
        # 5. Nível de Acesso
        nivel_acesso = st.selectbox("Nível de Acesso", ["SDR", "ADMIN"], help="ADMIN tem acesso total, SDR apenas aos seus dados.")
        
        # 6. Senha
        senha_inicial = st.text_input("Senha Inicial", type="password", placeholder="Defina uma senha provisória")

        st.markdown("<br>", unsafe_allow_html=True) # Espaçador

        # Botão de Submissão
        enviar = st.form_submit_button("🚀 Finalizar Cadastro", use_container_width=True)

        if enviar:
            # Validações de Preenchimento
            if not nome or not usuario or not prefixo_email or not senha_inicial:
                st.error("⚠️ Por favor, preencha todos os campos obrigatórios.")
            
            elif not validar_prefixo(prefixo_email):
                st.error("❌ O prefixo do e-mail é inválido! Não use espaços, acentos ou símbolos (permitido apenas letras, números, '.' e '_').")
            
            else:
                # Processamento e Formatação
                email_completo = f"{prefixo_email.strip().lower()}@grupoacelerador.com.br"
                telefone_formatado = formatar_telefone(telefone_raw)
                
                payload = {
                    "nome": nome.strip(),
                    "user": usuario.lower().strip(),
                    "senha": senha_inicial,
                    "email": email_completo,
                    "telefone": telefone_formatado,
                    "nivel": nivel_acesso.lower(),
                    "esta_ativo": True
                }

                try:
                    # Envio ao Supabase
                    supabase.table("usuarios").insert(payload).execute()
                    st.success(f"✅ Colaborador **{nome}** cadastrado com sucesso!")
                    st.info(f"📧 E-mail: {email_completo} | 📱 Tel: {telefone_formatado}")
                except Exception as e:
                    st.error(f"❌ Erro ao salvar no banco de dados: {str(e)}")

    # Exibição da Lista de Usuários Existentes (Opcional)
    with st.expander("📋 Ver Colaboradores Cadastrados"):
        try:
            res = supabase.table("usuarios").select("nome, user, email, nivel").execute()
            if res.data:
                st.table(res.data)
        except:
            st.info("Não foi possível carregar a lista de usuários.")