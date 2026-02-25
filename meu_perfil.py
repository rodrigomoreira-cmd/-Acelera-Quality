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
    # 🏅 LÓGICA DE MEDALHAS (GAMIFICAÇÃO MENSAL E VITALÍCIA)
    # ==========================================================
    df_mon_bruto = get_all_records_db("monitorias")
    df_comp_bruto = get_all_records_db("avaliacoes_comportamentais")
    df_cont_bruto = get_all_records_db("contestacoes")
    
    mes_atual = datetime.now().strftime('%m/%Y')
    medalhas_desbloqueadas = []
    
    # ----------------------------------------------------
    # Filtro de dados e conversão segura para o SDR logado
    # ----------------------------------------------------
    df_mon = pd.DataFrame()
    if df_mon_bruto is not None and not df_mon_bruto.empty:
        df_mon = df_mon_bruto[df_mon_bruto['sdr'].astype(str).str.strip().str.upper() == user_nome_exibicao.upper()].copy()
        if not df_mon.empty:
            df_mon['criado_em'] = pd.to_datetime(df_mon['criado_em'], errors='coerce')
            df_mon['nota'] = pd.to_numeric(df_mon['nota'], errors='coerce').fillna(0)

    # Separação do mês atual para os desafios mensais
    df_mon_mes = pd.DataFrame()
    if not df_mon.empty:
        df_mon_mes = df_mon[df_mon['criado_em'].dt.strftime('%m/%Y') == mes_atual].copy()

    df_comp = pd.DataFrame()
    if df_comp_bruto is not None and not df_comp_bruto.empty:
        df_comp = df_comp_bruto[df_comp_bruto['sdr_nome'].astype(str).str.strip().str.upper() == user_nome_exibicao.upper()].copy()

    df_cont = pd.DataFrame()
    if df_cont_bruto is not None and not df_cont_bruto.empty:
        col_sdr = 'sdr_nome' if 'sdr_nome' in df_cont_bruto.columns else 'sdr'
        df_cont = df_cont_bruto[df_cont_bruto[col_sdr].astype(str).str.strip().str.upper() == user_nome_exibicao.upper()].copy()

    # ----------------------------------------------------
    # REGRAS DE DESBLOQUEIO DE MEDALHAS
    # ----------------------------------------------------

    # 1. 🎯 Sniper (MENSAL: Tira nota 100% no mês atual)
    if not df_mon_mes.empty and (df_mon_mes['nota'] >= 100).any():
        medalhas_desbloqueadas.append("Sniper")

    # 2. 🔥 On Fire (MENSAL: 3 notas seguidas >= 90% no mês atual)
    if not df_mon_mes.empty and len(df_mon_mes) >= 3:
        notas_mes = df_mon_mes.sort_values('criado_em')['nota'].tolist()
        for i in range(len(notas_mes) - 2):
            if notas_mes[i] >= 90 and notas_mes[i+1] >= 90 and notas_mes[i+2] >= 90:
                medalhas_desbloqueadas.append("OnFire")
                break

    # 3. 🛡️ Muralha (MENSAL: Mês sem erros fatais/nota zero)
    if not df_mon_mes.empty and (df_mon_mes['nota'] > 0).all():
        medalhas_desbloqueadas.append("Muralha")

    # 4. ⭐ Talento Supremo (MENSAL: Quadrante Verde no mês atual)
    if not df_comp.empty and not df_mon_mes.empty:
        df_comp_mes = df_comp[df_comp['mes_referencia'] == mes_atual]
        if not df_comp_mes.empty:
            pdi_nota = (float(df_comp_mes.iloc[0]['media_comportamental']) / 5.0) * 100
            qa_media_mes = df_mon_mes['nota'].mean()
            if qa_media_mes >= 85 and pdi_nota >= 80:
                medalhas_desbloqueadas.append("Talento")

    # 5. ⚖️ Advogado (VITALÍCIA: Uma contestação Aceita na história)
    if not df_cont.empty and (df_cont['status'].astype(str).str.upper() == 'ACEITA').any():
        medalhas_desbloqueadas.append("Advogado")

    # 6. 📚 Sede de Evolução (VITALÍCIA: Possui pelo menos 1 PDI)
    if not df_comp.empty:
        medalhas_desbloqueadas.append("Evolucao")

    # ==========================================================
    # 🖼️ CABEÇALHO (ESTILO GITHUB)
    # ==========================================================
    todas_medalhas = {
        "Talento": {"icon": "⭐", "nome": "Talento Supremo", "desc": "Quadrante Verde no mês atual.", "cor": "#00cc96", "tipo": "MENSAL"},
        "Sniper": {"icon": "🎯", "nome": "Sniper da Qualidade", "desc": "Nota 100% no mês atual.", "cor": "#ff4b4b", "tipo": "MENSAL"},
        "OnFire": {"icon": "🔥", "nome": "On Fire", "desc": "3 calls > 90% seguidas no mês.", "cor": "#ff9900", "tipo": "MENSAL"},
        "Muralha": {"icon": "🛡️", "nome": "Muralha", "desc": "Mês sem erros fatais (Nota 0).", "cor": "#8c564b", "tipo": "MENSAL"},
        "Advogado": {"icon": "⚖️", "nome": "Advogado de Defesa", "desc": "Contestação aceita.", "cor": "#1f77b4", "tipo": "VITALÍCIA"},
        "Evolucao": {"icon": "📚", "nome": "Sede de Evolução", "desc": "Recebeu feedback de PDI.", "cor": "#9467bd", "tipo": "VITALÍCIA"}
    }

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
    # 🏆 VITRINE DE TROFÉUS (COM TIPO DA MEDALHA)
    # ==========================================================
    with st.expander("🏆 Sua Galeria de Troféus e Conquistas", expanded=True):
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        for idx, (m_id, m_dados) in enumerate(todas_medalhas.items()):
            conq = m_id in medalhas_desbloqueadas
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background-color: {m_dados['cor'] if conq else '#262626'}15; border: 1px solid {m_dados['cor'] if conq else '#444'}; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 15px; height: 170px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 35px;">{m_dados['icon'] if conq else '🔒'}</div>
                    <div style="font-weight: bold; font-size: 14px; color: white;">{m_dados['nome']}</div>
                    <div style="font-size: 11px; color: #aaa; margin-top: 5px;">{m_dados['desc']}</div>
                    <div style="font-size: 9px; color: {m_dados['cor'] if conq else '#666'}; margin-top: 8px; font-weight: bold;">{m_dados['tipo']}</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ==========================================================
    # ⚙️ CONFIGURAÇÕES (FOTO COM PREVIEW E SENHA FIX)
    # ==========================================================
    c_foto, c_senha = st.columns(2)

    with c_foto:
        st.subheader("🖼️ Foto de Perfil")
        novo_arquivo = st.file_uploader("Selecione uma foto:", type=['png', 'jpg', 'jpeg'], key="perfil_uploader", label_visibility="collapsed")
        
        # LÓGICA DE PREVIEW CORRIGIDA
        if novo_arquivo:
            st.markdown("**Prévia da nova foto:**")
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
        # SUBMIT DO FORMULÁRIO CORRIGIDO
        with st.form("form_senha_perfil_final", clear_on_submit=True):
            s_at = st.text_input("Senha Atual", type="password")
            s_nv = st.text_input("Nova Senha", type="password")
            s_cf = st.text_input("Confirmar", type="password")
            
            # O st.form_submit_button PRECISA ser o último elemento do escopo
            btn_save = st.form_submit_button("Atualizar Senha", use_container_width=True)
            
            if btn_save:
                if s_nv != s_cf: 
                    st.error("As senhas não coincidem.")
                elif len(s_nv) < 4:
                    st.error("A nova senha deve ter pelo menos 4 caracteres.")
                else:
                    h_dig = hash_password(s_at)
                    if h_dig == senha_banco or s_at.strip() == senha_banco:
                        supabase.table("usuarios").update({"senha": hash_password(s_nv)}).eq("id", meu_id).execute()
                        st.success("Senha alterada com sucesso!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else: 
                        st.error("Senha atual incorreta.")