import streamlit as st
import hashlib
import re
import time
import pandas as pd
from datetime import datetime
from database import supabase, registrar_auditoria, get_all_records_db

def hash_password(password):
    """Gera o hash SHA-256 da senha."""
    return hashlib.sha256(str.encode(password.strip())).hexdigest()

def limpar_nome_arquivo(nome):
    nome_limpo = re.sub(r'[^a-zA-Z0-9]', '_', nome)
    return nome_limpo.lower()

def render_meu_perfil():
    # 1. Recupera sessão e limpa espaços
    user_login = st.session_state.get('user_login', '').strip()
    
    if not user_login:
        st.error("Sessão inválida. Faça login novamente.")
        return

    # 2. Busca no banco informações do usuário
    try:
        res = supabase.table("usuarios").select("*").ilike("user", user_login).execute()
        
        if res.data and len(res.data) > 0:
            user_info = res.data[0]
            foto_atual = user_info.get('foto_url')
            senha_banco = user_info.get('senha') 
            user_nome_exibicao = user_info.get('nome', 'Usuário')
            nivel = user_info.get('nivel')
            esta_ativo = user_info.get('esta_ativo')
            meu_id = user_info.get('id')
            dept_usuario = user_info.get('departamento', 'Não Informado')
        else:
            st.warning(f"⚠️ Usuário não encontrado no banco.")
            return
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return

    # ==========================================================
    # 🏅 LÓGICA DE MEDALHAS (GAMIFICAÇÃO)
    # ==========================================================
    df_mon_bruto = get_all_records_db("monitorias")
    df_comp_bruto = get_all_records_db("avaliacoes_comportamentais")
    
    medalhas = []
    mes_atual = datetime.now().strftime('%m/%Y')
    
    # Filtro de dados para este usuário específico
    df_mon = pd.DataFrame()
    if df_mon_bruto is not None and not df_mon_bruto.empty:
        df_mon = df_mon_bruto[df_mon_bruto['sdr'].str.strip().str.upper() == user_nome_exibicao.upper()].copy()
        if not df_mon.empty:
            df_mon['criado_em'] = pd.to_datetime(df_mon['criado_em'], errors='coerce')
            df_mon = df_mon.sort_values('criado_em', ascending=False)

    df_comp = pd.DataFrame()
    if df_comp_bruto is not None and not df_comp_bruto.empty:
        df_comp = df_comp_bruto[df_comp_bruto['sdr_nome'].str.strip().str.upper() == user_nome_exibicao.upper()].copy()

    # Cálculo das conquistas
    if not df_mon.empty:
        # 🥇 Sniper (100% na última)
        if float(df_mon.iloc[0]['nota']) == 100.0:
            medalhas.append({"icon": "🥇", "nome": "Sniper", "desc": "Sua última monitoria foi 100%!"})
        
        # 🛡️ Muralha (Zero fatais no mês)
        df_mon_mes = df_mon[df_mon['criado_em'].dt.strftime('%m/%Y') == mes_atual]
        if not df_mon_mes.empty and all(float(nota) > 0 for nota in df_mon_mes['nota']):
            medalhas.append({"icon": "🛡️", "nome": "Muralha", "desc": "Nenhum Erro Fatal este mês!"})

    # ⭐ Talento (Quadrante Verde na Matriz 9-Box)
    if not df_mon.empty and not df_comp.empty:
        df_comp_mes = df_comp[df_comp['mes_referencia'] == mes_atual]
        if not df_comp_mes.empty:
            pdi_nota = (float(df_comp_mes.iloc[0]['media_comportamental']) / 5.0) * 100
            qa_media_mes = df_mon[df_mon['criado_em'].dt.strftime('%m/%Y') == mes_atual]['nota'].mean()
            if qa_media_mes >= 85 and pdi_nota >= 80:
                medalhas.append({"icon": "⭐", "nome": "Talento", "desc": "Elite! Você está no Quadrante Verde da Matriz."})

    # ==========================================================
    # 🖼️ CABEÇALHO ESTILO GITHUB (FOTO + NOME + MEDALHAS)
    # ==========================================================
    url_foto_header = foto_atual if foto_atual else f"https://ui-avatars.com/api/?name={user_nome_exibicao.replace(' ', '+')}&background=ea580c&color=fff"
    
    html_badges = ""
    for m in medalhas:
        html_badges += f'''
        <div title="{m['desc']}" style="display: inline-flex; align-items: center; background: #262626; border: 1px solid #444; border-radius: 15px; padding: 3px 10px; margin-left: 8px; cursor: help; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
            <span style="font-size: 14px; margin-right: 5px;">{m['icon']}</span>
            <span style="font-size: 11px; color: white; font-weight: bold; margin-right: 5px;">{m['nome']}</span>
            <span style="color: #888; font-size: 10px; background: #111; border-radius: 50%; width: 14px; height: 14px; display: flex; align-items: center; justify-content: center;">?</span>
        </div>
        '''

    st.markdown(f'''
    <div style="display: flex; align-items: center; background: #1a1a1a; padding: 25px; border-radius: 15px; border: 1px solid #333; margin-bottom: 25px;">
        <img src="{url_foto_header}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #ea580c; object-fit: cover; flex-shrink: 0;">
        <div style="margin-left: 20px; flex-grow: 1;">
            <div style="display: flex; align-items: center; flex-wrap: wrap;">
                <h2 style="margin: 0; color: white; font-size: 24px; white-space: nowrap;">{user_nome_exibicao}</h2>
                <div style="display: flex; align-items: center; margin-top: 5px;">{html_badges}</div>
            </div>
            <p style="margin: 5px 0 0 0; color: #888; font-size: 14px;">{dept_usuario} • {user_login}</p>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # --- TELA DE PERFIL ORIGINAL CONTINUA ABAIXO ---

    # FOTO (Upload)
    st.subheader("🖼️ Trocar Foto de Perfil")
    with st.container(border=True):
        novo_arquivo = st.file_uploader("Escolha uma imagem (PNG/JPG)", type=['png', 'jpg'])
        if novo_arquivo and st.button("Salvar Nova Foto"):
            try:
                ext = novo_arquivo.name.split('.')[-1]
                nome_arq = limpar_nome_arquivo(user_login.split('@')[0]) + f".{ext}"
                supabase.storage.from_("avatars").upload(
                    path=nome_arq, file=novo_arquivo.getvalue(), 
                    file_options={"upsert": "true", "content-type": f"image/{ext}"}
                )
                url = supabase.storage.from_("avatars").get_public_url(nome_arq)
                supabase.table("usuarios").update({"foto_url": url}).eq("id", meu_id).execute()
                
                registrar_auditoria(acao="ALTERAÇÃO DE PERFIL", detalhes="O utilizador atualizou a sua foto de perfil.")
                
                st.success("Foto salva!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar foto: {e}")

    # DADOS
    st.subheader("📋 Informações da Conta")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.write(f"**Nome:** {user_nome_exibicao}")
        c1.write(f"**Login:** {user_login}")
        c2.write(f"**Nível:** {nivel}")
        c2.write(f"**Status:** {'✅ Ativo' if esta_ativo else '❌ Inativo'}")

    # TROCA DE SENHA
    st.subheader("🔐 Segurança")
    with st.form("frm_senha", clear_on_submit=True):
        st.markdown("#### Alterar Senha")
        s_atual = st.text_input("Senha Atual", type="password")
        s_nova = st.text_input("Nova Senha", type="password")
        s_conf = st.text_input("Confirmar Nova Senha", type="password")
        
        if st.form_submit_button("Atualizar Senha"):
            if not s_atual or not s_nova:
                st.error("Preencha todos os campos de senha.")
            elif s_nova != s_conf:
                st.error("A nova senha e a confirmação não coincidem.")
            else:
                hash_digitado = hash_password(s_atual)
                senha_correta = False
                
                if hash_digitado == senha_banco:
                    senha_correta = True
                elif s_atual.strip() == senha_banco:
                    senha_correta = True
                    st.info("Senha antiga detectada e atualizada para criptografia moderna.")

                if senha_correta:
                    novo_hash = hash_password(s_nova)
                    supabase.table("usuarios").update({"senha": novo_hash}).eq("id", meu_id).execute()
                    
                    registrar_auditoria(acao="ALTEROU PRÓPRIA SENHA", detalhes="O utilizador alterou a sua própria senha com sucesso.")
                    
                    st.success("Senha atualizada e protegida!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("A senha atual informada está incorreta.")