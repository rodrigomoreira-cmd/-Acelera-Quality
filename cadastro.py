import streamlit as st
import re
from database import supabase

def validar_prefixo(prefixo):
    """Permite apenas letras, números, pontos e sublinhados."""
    padrao = r'^[a-zA-Z0-9._]+$'
    return re.match(padrao, prefixo) is not None

def formatar_telefone(tel):
    """Aplica a máscara (XX) XXXXX-XXXX."""
    numeros = re.sub(r'\D', '', tel)
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return tel

def render_cadastro():
    st.title("👥 Cadastro de Novo Colaborador (SDR)")
    st.markdown("Preencha as informações abaixo para criar um novo acesso ao sistema.")

    # Usando um container para manter o layout limpo
    with st.container():
        # 1. Informações Básicas
        nome = st.text_input("Nome Completo", placeholder="Ex: João Silva")
        usuario = st.text_input("Usuário de Acesso", placeholder="Ex: joao.sdr")
        
        # 2. E-mail Institucional (Layout Verticalizado com Prefixo e Domínio)
        st.write("**E-mail Institucional**")
        col_pref, col_dom = st.columns([2, 1])
        with col_pref:
            prefixo_email = st.text_input("Prefixo do E-mail", placeholder="Ex: joao.silva", label_visibility="collapsed")
        with col_dom:
            st.info("@grupoacelerador.com.br")
        
        # 3. Contato e Permissão
        telefone_raw = st.text_input("Telefone de Contato", placeholder="DDD + Número")
        nivel_acesso = st.selectbox("Nível de Acesso", ["SDR", "ADMIN"])
        
        # 4. Segurança
        senha = st.text_input("Senha Inicial", type="password", placeholder="Digite a senha temporária")

    st.divider()

    if st.button("🚀 Finalizar Cadastro", use_container_width=True):
        # Validações antes de salvar
        if not nome or not usuario or not prefixo_email or not senha:
            st.error("⚠️ Por favor, preencha todos os campos obrigatórios.")
        elif not validar_prefixo(prefixo_email):
            st.error("❌ O prefixo do e-mail não pode conter espaços ou caracteres especiais (use apenas letras, números, '.' ou '_').")
        else:
            # Preparar dados para o Supabase
            email_completo = f"{prefixo_email.strip().lower()}@grupoacelerador.com.br"
            telefone_formatado = formatar_telefone(telefone_raw)
            
            novo_usuario = {
                "nome": nome.strip(),
                "user": usuario.strip().lower(),
                "email": email_completo,
                "telefone": telefone_formatado,
                "nivel": nivel_acesso,
                "senha": senha
            }

            try:
                # Tenta inserir no banco de dados
                res = supabase.table("usuarios").insert(novo_usuario).execute()
                
                if res.data:
                    st.success(f"✅ Colaborador **{nome}** cadastrado com sucesso!")
                    st.balloons()
                    # Limpar campos após sucesso (opcional, via rerun)
                    # st.rerun()
                else:
                    st.error("❌ Erro ao salvar no banco de dados. Verifique se o usuário já existe.")
            except Exception as e:
                st.error(f"❌ Erro de conexão: {str(e)}")