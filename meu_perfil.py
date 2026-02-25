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
    # 1. Recupera sessão
    user_login = st.session_state.get('user_login', '').strip()
    
    if not user_login:
        st.error("Sessão inválida. Faça login novamente.")
        return

    # 2. Busca informações do usuário no banco
    try:
        res = supabase.table("usuarios").select("*").ilike("user", user_login).execute()
        
        if res.data and len(res.data) > 0:
            user_info = res.data[0]
            foto_atual = user_info.get('foto_url')
            senha_banco = user_info.get('senha') 
            user_nome_exibicao = user_info.get('nome', 'Usuário').strip()
            nivel = user_info.get('nivel')
            meu_id = user_info.get('id')
            dept_usuario = user_info.get('departamento', 'Não Informado')
        else:
            st.warning("⚠️ Usuário não encontrado.")
            return
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return

    # ==========================================================
    # 🏅 LÓGICA DE MEDALHAS (GAMIFICAÇÃO)
    # ==========================================================
    df_mon_bruto = get_all_records_db("monitorias")
    df_comp_bruto = get_all_records_db("avaliacoes_comportamentais")
    df_cont_bruto = get_all_records_db("contestacoes")
    
    mes_atual = datetime.now().strftime('%m/%Y')
    medalhas_desbloqueadas = []
    
    # Filtro de dados do usuário
    df_mon = pd.DataFrame()
    if df_mon_bruto is not None and not df_mon_bruto.empty:
        df_mon = df_mon_bruto[df_mon_bruto['sdr'].astype(str).str.strip().str.upper() == user_nome_exibicao.upper()].copy()
        if not df_mon.empty:
            df_mon['criado_em'] = pd.to_datetime(df_mon['criado_em'], errors='coerce')
            df_mon['nota'] = pd.to_numeric(df_mon['nota'], errors='coerce').fillna(0)

    df_comp = pd.DataFrame()
    if df_comp_bruto is not None and not df_comp_bruto.empty:
        df_comp = df_comp_bruto[df_comp_bruto['sdr_nome'].astype(str).str.strip().str.upper() == user_nome_exibicao.upper()].copy()

    df_cont = pd.DataFrame()
    if df_cont_bruto is not None and not df_cont_bruto.empty:
        col_sdr = 'sdr_nome' if 'sdr_nome' in df_cont_bruto.columns else 'sdr'
        if col_sdr in df_cont_bruto.columns:
            df_cont = df_cont_bruto[df_cont_bruto[col_sdr].astype(str).str.strip().str.upper() == user_nome_exibicao.upper()].copy()

    # Regras de Desbloqueio
    if not df_mon.empty and (df_mon['nota'] >= 100).any(): medalhas_desbloqueadas.append("Sniper")
    if not df_mon.empty and len(df_mon) >= 3:
        notas = df_mon.sort_values('criado_em', ascending=False)['nota'].tolist()
        for i in range(len(notas) - 2):
            if notas[i] >= 90 and notas[i+1] >= 90 and notas[i+2] >= 90:
                medalhas_desbloqueadas.append("OnFire")
                break
    if not df_cont.empty and (df_cont['status'].astype(str).str.upper() == 'ACEITA').any(): medalhas_desbloqueadas.append("Advogado")
    if not df_comp.empty: medalhas_desbloqueadas.append("Evolucao")

    # Dicionário de Definições
    todas_medalhas = {
        "Talento": {"icon": "⭐", "nome": "Talento Supremo", "desc": "Quadrante Verde na Matriz 9-Box.", "cor": "#00cc96"},
        "Sniper": {"icon": "🎯", "nome": "Sniper da Qualidade", "desc": "Nota 100% em monitoria técnica.", "cor": "#ff4b4b"},
        "OnFire": {"icon": "🔥", "nome": "On Fire", "desc": "3 monitorias seguidas acima de 90%.", "cor": "#ff9900"},
        "Advogado": {"icon": "⚖️", "nome": "Advogado de Defesa", "desc": "Contestação aceita com sucesso.", "cor": "#1f77b4"},
        "Evolucao": {"icon": "📚", "nome": "Sede de Evolução", "desc": "Já recebeu feedback de PDI.", "cor": "#9467bd"},
        "Muralha": {"icon": "🛡️", "nome": "Muralha", "desc": "Mês sem erros fatais.", "cor": "#8c564b"}
    }

    # ==========================================================
    # 🖼️ CABEÇALHO (ESTILO GITHUB)
    # ==========================================================
    url_foto_header = foto_atual if foto_atual else f"https://ui-avatars.com/api/?name={user_nome_exibicao.replace(' ', '+')}&background=ea580c&color=fff"
    
    html_badges_topo = ""
    for m_id in medalhas_desbloqueadas:
        m = todas_medalhas[m_id]
        html_badges_topo += f'<div title="{m["desc"]}" style="display: inline-flex; align-items: center; background: {m["cor"]}22; border: 1px solid {m["cor"]}88; border-radius: 15px; padding: 3px 10px; margin-right: 8px; margin-top: 5px;"><span style="font-size: 14px; margin-right: 5px;">{m["icon"]}</span><span style="font-size: 11px; color: {m["cor"]}; font-weight: bold;">{m["nome"]}</span></div>'

    st.markdown(f'''
    <div style="display: flex; align-items: center; background: #1a1a1a; padding: 25px; border-radius: 15px; border: 1px solid #333; margin-bottom: 25px;">
        <img src="{url_foto_header}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #ea580c; object-fit: cover;">
        <div style="margin-left: 20px;">
            <h2 style="margin: 0; color: white; font-size: 24px;">{user_nome_exibicao}</h2>
            <p style="margin: 2px 0 10px 0; color: #888; font-size: 14px;">{dept_usuario} • Nível: {nivel}</p>
            <div style="display: flex; flex-wrap: wrap;">{html_badges_topo}</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # ==========================================================
    # 🏆 VITRINE DE TROFÉUS
    # ==========================================================
    with st.expander("🏆 Sua Galeria de Troféus e Conquistas", expanded=True):
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        for idx, (m_id, m_dados) in enumerate(todas_medalhas.items()):
            conq = m_id in medalhas_desbloqueadas
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background-color: {m_dados['cor'] if conq else '#262626'}15; border: 1px solid {m_dados['cor'] if conq else '#444'}; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 15px; height: 160px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 35px;">{m_dados['icon'] if conq else '🔒'}</div>
                    <div style="font-weight: bold; font-size: 14px; color: white;">{m_dados['nome']}</div>
                    <div style="font-size: 11px; color: #aaa; margin-top: 5px;">{m_dados['desc']}</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ==========================================================
    # ⚙️ CONFIGURAÇÕES (FOTO COM PREVIEW E SENHA)
    # ==========================================================
    c_foto, c_senha = st.columns(2)

    with c_foto:
        st.subheader("🖼️ Foto de Perfil")
        novo_arquivo = st.file_uploader("Selecione uma foto:", type=['png', 'jpg', 'jpeg'], key="perfil_uploader", label_visibility="collapsed")
        
        # --- LÓGICA DE PREVIEW ---
        if novo_arquivo:
            st.markdown("**Prévia da nova foto:**")
            # Mostra a imagem redonda como ficará no perfil
            st.image(novo_arquivo, width=120)
            
            if st.button("✅ Confirmar e Salvar Foto", use_container_width=True):
                try:
                    ext = novo_arquivo.name.split('.')[-1]
                    nome_arq = limpar_nome_arquivo(user_login.split('@')[0]) + f".{ext}"
                    supabase.storage.from_("avatars").upload(
                        path=nome_arq, file=novo_arquivo.getvalue(), 
                        file_options={"upsert": "true", "content-type": f"image/{ext}"}
                    )
                    url = supabase.storage.from_("avatars").get_public_url(nome_arq)
                    supabase.table("usuarios").update({"foto_url": url}).eq("id", meu_id).execute()
                    
                    st.success("Foto atualizada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    with c_senha:
        st.subheader("🔐 Segurança")
        with st.form("form_senha_perfil", clear_on_submit=True):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            s_cf = st.text_input("Confirmar", type="password")
            if st.form_submit_button("Atualizar Senha", use_container_width=True):
                if s_nv != s_cf: st.error("As senhas não coincidem.")
                else:
                    h_dig = hash_password(s_at)
                    if h_dig == senha_banco or s_at.strip() == senha_banco:
                        supabase.table("usuarios").update({"senha": hash_password(s_nv)}).eq("id", meu_id).execute()
                        st.success("Senha alterada!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Senha atual incorreta.")