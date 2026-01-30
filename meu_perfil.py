import streamlit as st
from database import supabase, registrar_auditoria
import hashlib
import re
import time

def hash_password(password):
    """Gera o hash SHA-256 para comparação segura de senhas."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def limpar_nome_arquivo(nome):
    """Remove caracteres especiais para evitar erros de URL no Storage do Supabase."""
    nome_limpo = re.sub(r'[^a-zA-Z0-9]', '_', nome)
    return nome_limpo.lower()

def render_meu_perfil():
    st.title("👤 Meu Perfil")
    
    # Usamos o login (user) como chave primária para busca, pois o nome pode ter duplicatas
    user_nome_exibicao = st.session_state.get('user_nome')
    user_login = st.session_state.get('user_login') # Deve estar no session_state no login
    nivel = st.session_state.get('nivel')

    # Busca dados atuais do usuário logado
    try:
        # Busca pela coluna 'user' (e-mail) que é única
        res = supabase.table("usuarios").select("*").eq("user", user_login).single().execute()
        user_info = res.data if res.data else {}
        foto_atual = user_info.get('foto_url')
    except Exception as e:
        st.error(f"Erro ao carregar dados do perfil: {e}")
        user_info, foto_atual = {}, None

    # --- SEÇÃO 1: FOTO DE PERFIL ---
    st.subheader("🖼️ Foto de Perfil")
    with st.container(border=True):
        arquivo_foto = st.file_uploader("Alterar foto (PNG ou JPG)", type=['png', 'jpg', 'jpeg'])
        
        if arquivo_foto:
            # PRÉVIA
            st.markdown("<p style='text-align: center; color: #ff4b4b;'><b>Prévia da nova foto:</b></p>", unsafe_allow_html=True)
            st.image(arquivo_foto, width=150)
            
            if st.button("✅ Confirmar e Salvar Nova Foto", type="primary", use_container_width=True):
                try:
                    ext = arquivo_foto.name.split('.')[-1]
                    # Nome do arquivo baseado no login para ser único
                    nome_base = limpar_nome_arquivo(user_login.split('@')[0])
                    file_path = f"avatar_{nome_base}.{ext}"
                    
                    # Upload para o Bucket 'avatars' (certifique-se que o bucket é público no Supabase)
                    supabase.storage.from_("avatars").upload(
                        path=file_path, 
                        file=arquivo_foto.getvalue(), 
                        file_options={"upsert": "true", "content-type": f"image/{ext}"}
                    )
                    
                    # Gera URL Pública
                    url_nova = supabase.storage.from_("avatars").get_public_url(file_path)
                    
                    # Atualiza o campo foto_url na tabela de usuários
                    supabase.table("usuarios").update({"foto_url": url_nova}).eq("user", user_login).execute()
                    
                    st.success("Foto atualizada com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Falha ao processar imagem: {e}")
        
        elif foto_atual:
            st.markdown(f"""
                <div style="display: flex; flex-direction: column; align-items: center; padding: 10px;">
                    <img src="{foto_atual}" style="width: 150px; height: 150px; border-radius: 50%; object-fit: cover; border: 3px solid #ff4b4b;">
                    <p style="color: gray; margin-top: 10px;">Foto atual do perfil</p>
                </div>
            """, unsafe_allow_html=True)

    # --- SEÇÃO 2: DADOS ---
    st.subheader("📋 Informações da Conta")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.write(f"**Nome:** {user_nome_exibicao}")
        c1.write(f"**E-mail:** {user_login}")
        c2.write(f"**Nível de Acesso:** {nivel}")
        c2.write(f"**Status:** ✅ Ativo")

    # --- SEÇÃO 3: TROCA DE SENHA ---
    st.subheader("🔐 Alterar Senha")
    with st.form("form_senha", border=True):
        st.info("Para sua segurança, a nova senha deve ser diferente da atual.")
        s_atual = st.text_input("Senha Atual", type="password")
        col_s1, col_s2 = st.columns(2)
        s_nova = col_s1.text_input("Nova Senha", type="password")
        s_conf = col_s2.text_input("Confirme a Nova Senha", type="password")
        
        if st.form_submit_button("Atualizar Minha Senha", use_container_width=True):
            if not s_atual or not s_nova:
                st.error("Preencha todos os campos de senha.")
            elif s_nova != s_conf:
                st.error("As novas senhas digitadas não coincidem.")
            elif len(s_nova) < 6:
                st.error("A nova senha deve ter pelo menos 6 caracteres.")
            elif hash_password(s_atual) != user_info.get('senha'):
                st.error("A 'Senha Atual' digitada está incorreta.")
            else:
                try:
                    # Atualiza com o novo HASH
                    supabase.table("usuarios").update({"senha": hash_password(s_nova)}).eq("user", user_login).execute()
                    registrar_auditoria("ALT_SENHA", user_nome_exibicao, "Usuário alterou a própria senha via perfil.")
                    st.success("Senha alterada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao atualizar senha: {e}")