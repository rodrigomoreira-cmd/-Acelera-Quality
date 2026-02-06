import streamlit as st
import hashlib
import re
import time
from database import supabase, registrar_auditoria

def hash_password(password):
    """Gera o hash SHA-256 da senha."""
    return hashlib.sha256(str.encode(password.strip())).hexdigest()

def limpar_nome_arquivo(nome):
    nome_limpo = re.sub(r'[^a-zA-Z0-9]', '_', nome)
    return nome_limpo.lower()

def render_meu_perfil():
    st.title("👤 Meu Perfil")
    
    # 1. Recupera sessão e limpa espaços
    user_login = st.session_state.get('user_login', '').strip()
    
    # --- DIAGNÓSTICO VISUAL (Pode remover depois) ---
    # st.write(f"Login da Sessão: `{user_login}`")
    
    if not user_login:
        st.error("Sessão inválida. Faça login novamente.")
        return

    # 2. Busca no banco (Usando ILIKE para ignorar maiúsculas/minúsculas)
    try:
        # Tenta buscar ignorando case sensitive
        res = supabase.table("usuarios").select("*").ilike("user", user_login).execute()
        
        if res.data and len(res.data) > 0:
            user_info = res.data[0]
            foto_atual = user_info.get('foto_url')
            senha_banco = user_info.get('senha') # No seu print a coluna é 'senha'
            
            user_nome_exibicao = user_info.get('nome', 'Usuário')
            nivel = user_info.get('nivel')
            esta_ativo = user_info.get('esta_ativo')
        else:
            st.warning(f"⚠️ Usuário não encontrado no banco.")
            st.markdown(f"O sistema buscou por: **{user_login}** na coluna **user**.")
            st.markdown("Sugestão: Verifique no Supabase se o RLS (Row Level Security) está desativado.")
            return

    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return

    # --- TELA DE PERFIL ---

    # FOTO
    st.subheader("🖼️ Foto")
    with st.container(border=True):
        c_img, c_up = st.columns([1, 3])
        with c_img:
            if foto_atual:
                st.image(foto_atual, width=100)
            else:
                st.markdown("👤")
        with c_up:
            novo_arquivo = st.file_uploader("Trocar foto", type=['png', 'jpg'])
            if novo_arquivo and st.button("Salvar Foto"):
                try:
                    ext = novo_arquivo.name.split('.')[-1]
                    nome_arq = limpar_nome_arquivo(user_login.split('@')[0]) + f".{ext}"
                    supabase.storage.from_("avatars").upload(
                        path=nome_arq, file=novo_arquivo.getvalue(), 
                        file_options={"upsert": "true", "content-type": f"image/{ext}"}
                    )
                    url = supabase.storage.from_("avatars").get_public_url(nome_arq)
                    supabase.table("usuarios").update({"foto_url": url}).eq("id", user_info['id']).execute()
                    st.success("Foto salva!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    # DADOS
    st.subheader("📋 Dados")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.write(f"**Nome:** {user_nome_exibicao}")
        c1.write(f"**Login:** {user_login}")
        c2.write(f"**Nível:** {nivel}")
        c2.write(f"**Status:** {'✅ Ativo' if esta_ativo else '❌ Inativo'}")

    # TROCA DE SENHA (COM CORREÇÃO PARA SENHA ANTIGA)
    st.subheader("🔐 Alterar Senha")
    with st.form("frm_senha", clear_on_submit=True):
        s_atual = st.text_input("Senha Atual", type="password")
        s_nova = st.text_input("Nova Senha", type="password")
        s_conf = st.text_input("Confirmar Nova Senha", type="password")
        
        if st.form_submit_button("Atualizar"):
            if not s_atual or not s_nova:
                st.error("Preencha tudo.")
            elif s_nova != s_conf:
                st.error("Senhas novas não batem.")
            else:
                # --- LÓGICA HÍBRIDA (IMPORTANTE) ---
                # 1. Calcula o hash do que foi digitado
                hash_digitado = hash_password(s_atual)
                
                # 2. Verifica: É igual ao hash? OU É igual ao texto puro (senha antiga)?
                senha_correta = False
                
                # Teste 1: Senha já está criptografada no banco?
                if hash_digitado == senha_banco:
                    senha_correta = True
                # Teste 2: Senha no banco é antiga (texto puro 1915...)?
                elif s_atual.strip() == senha_banco:
                    senha_correta = True
                    st.info("Detectamos que sua senha era antiga. Atualizando criptografia...")

                if senha_correta:
                    # Salva a nova já como Hash
                    novo_hash = hash_password(s_nova)
                    supabase.table("usuarios").update({"senha": novo_hash}).eq("id", user_info['id']).execute()
                    
                    registrar_auditoria("ALT_SENHA", user_nome_exibicao, "Trocou a senha.")
                    st.success("Senha atualizada e protegida!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Senha atual incorreta.")