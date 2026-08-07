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
    nome_limpo = re.sub(r"[^a-zA-Z0-9]", "_", nome)
    return nome_limpo.lower()


def render_meu_perfil():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados. Verifique suas credenciais.")
        return
    # ------------------------------------------------------------------

    # 🎨 PALETA DE CORES SISTÊMICA
    COR_PRINCIPAL = "#FF7A00"  # Laranja vibrante principal
    COR_SUCESSO = "#00E676"  # Verde neon
    COR_TEXTO = "#A0AEC0"

    # 1. Recupera sessão
    user_login = st.session_state.get("user_login", "").strip()

    if not user_login:
        st.error("Sessão inválida. Faça login novamente.")
        return

    # 2. Busca informações do usuário no banco
    try:
        res = supabase.table("usuarios").select("*").ilike("user", user_login).execute()  # type: ignore

        if (
            hasattr(res, "data")
            and res.data
            and isinstance(res.data, list)
            and len(res.data) > 0
        ):
            user_info = res.data[0]

            # BLINDAGEM PYLANCE: Garante que o dado é um Dicionário antes de usar .get()
            if isinstance(user_info, dict):
                foto_atual = user_info.get("foto_url")
                senha_banco = user_info.get("senha")
                nome_bruto = user_info.get("nome", "Usuário")
                user_nome_exibicao = (
                    str(nome_bruto).strip() if nome_bruto else "Usuário"
                )
                nivel = user_info.get("nivel")
                meu_id = user_info.get("id")
                dept_usuario = user_info.get("departamento", "Não Informado")
            else:
                st.warning("⚠️ Erro: Formato de usuário inválido no banco de dados.")
                return
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

    mes_atual = datetime.now().strftime("%m/%Y")
    medalhas_desbloqueadas = []

    # Filtro de dados e conversão segura para o SDR logado
    df_mon = pd.DataFrame()
    if df_mon_bruto is not None and not df_mon_bruto.empty:
        df_mon = df_mon_bruto[
            df_mon_bruto["sdr"].astype(str).str.strip().str.upper()
            == user_nome_exibicao.upper()
        ].copy()
        if not df_mon.empty:
            df_mon["criado_em"] = pd.to_datetime(df_mon["criado_em"], errors="coerce")
            df_mon["nota"] = pd.to_numeric(df_mon["nota"], errors="coerce").fillna(0)

    # Separação do mês atual para os desafios mensais
    df_mon_mes = pd.DataFrame()
    if not df_mon.empty:
        df_mon_mes = df_mon[
            df_mon["criado_em"].dt.strftime("%m/%Y") == mes_atual
        ].copy()

    df_comp = pd.DataFrame()
    if df_comp_bruto is not None and not df_comp_bruto.empty:
        df_comp = df_comp_bruto[
            df_comp_bruto["sdr_nome"].astype(str).str.strip().str.upper()
            == user_nome_exibicao.upper()
        ].copy()

    df_cont = pd.DataFrame()
    if df_cont_bruto is not None and not df_cont_bruto.empty:
        col_sdr = "sdr_nome" if "sdr_nome" in df_cont_bruto.columns else "sdr"
        df_cont = df_cont_bruto[
            df_cont_bruto[col_sdr].astype(str).str.strip().str.upper()
            == user_nome_exibicao.upper()
        ].copy()

    # ----------------------------------------------------
    # REGRAS DE DESBLOQUEIO DE MEDALHAS
    # ----------------------------------------------------
    # 1. Sniper (MENSAL: Tira nota 100% no mês atual)
    if not df_mon_mes.empty and (df_mon_mes["nota"] >= 100).any():
        medalhas_desbloqueadas.append("Sniper")

    # 2. 🔥 On Fire (MENSAL: 3 notas seguidas >= 90% no mês atual)
    if not df_mon_mes.empty and len(df_mon_mes) >= 3:
        notas_mes = df_mon_mes.sort_values("criado_em")["nota"].tolist()
        for i in range(len(notas_mes) - 2):
            if notas_mes[i] >= 90 and notas_mes[i + 1] >= 90 and notas_mes[i + 2] >= 90:
                medalhas_desbloqueadas.append("OnFire")
                break

    # 3. Muralha (MENSAL: Mês sem erros fatais/nota zero)
    if not df_mon_mes.empty and (df_mon_mes["nota"] > 0).all():
        medalhas_desbloqueadas.append("Muralha")

    # 4. Talento Supremo (MENSAL: Quadrante Verde no mês atual)
    if not df_comp.empty and not df_mon_mes.empty:
        df_comp_mes = df_comp[df_comp["mes_referencia"] == mes_atual]
        if not df_comp_mes.empty:
            pdi_nota = (
                float(str(df_comp_mes.iloc[0]["media_comportamental"])) / 5.0
            ) * 100
            qa_media_mes = df_mon_mes["nota"].mean()
            if qa_media_mes >= 85 and pdi_nota >= 80:
                medalhas_desbloqueadas.append("Talento")

    # 5. Advogado (VITALÍCIA: Uma contestação Aceita na história)
    if (
        not df_cont.empty
        and (df_cont["status"].astype(str).str.upper() == "ACEITA").any()
    ):
        medalhas_desbloqueadas.append("Advogado")

    # 6. Sede de Evolução (VITALÍCIA: Possui pelo menos 1 PDI)
    if not df_comp.empty:
        medalhas_desbloqueadas.append("Evolucao")

    # ==========================================================
    # 🖼️ CABEÇALHO (ESTILO SAAS PREMIUM)
    # ==========================================================
    todas_medalhas = {
        "Talento": {
            "icon": "⭐",
            "nome": "Talento Supremo",
            "desc": "Quadrante Verde no mês.",
            "cor": COR_SUCESSO,
            "tipo": "MENSAL",
        },
        "Sniper": {
            "icon": "🎯",
            "nome": "Sniper da Qualidade",
            "desc": "Nota 100% no mês atual.",
            "cor": COR_PRINCIPAL,
            "tipo": "MENSAL",
        },
        "OnFire": {
            "icon": "🔥",
            "nome": "On Fire",
            "desc": "3 calls > 90% seguidas.",
            "cor": "#FFCC00",
            "tipo": "MENSAL",
        },
        "Muralha": {
            "icon": "🛡️",
            "nome": "Muralha",
            "desc": "Mês sem erros fatais (Nota 0).",
            "cor": "#A0AEC0",
            "tipo": "MENSAL",
        },
        "Advogado": {
            "icon": "⚖️",
            "nome": "Advogado de Defesa",
            "desc": "Contestação aceita.",
            "cor": "#1f77b4",
            "tipo": "VITALÍCIA",
        },
        "Evolucao": {
            "icon": "📚",
            "nome": "Sede de Evolução",
            "desc": "Recebeu feedback de PDI.",
            "cor": "#9467bd",
            "tipo": "VITALÍCIA",
        },
    }

    url_foto_header = (
        str(foto_atual)
        if foto_atual
        else f"https://ui-avatars.com/api/?name={user_nome_exibicao.replace(' ', '+')}&background=ea580c&color=fff"
    )

    html_badges_topo = ""
    for m_id in medalhas_desbloqueadas:
        m = todas_medalhas[m_id]
        html_badges_topo += f'<div title="{m["desc"]}" style="display: inline-flex; align-items: center; background: {m["cor"]}15; border: 1px solid {m["cor"]}50; border-radius: 12px; padding: 4px 12px; margin-right: 8px; margin-top: 6px;"><span style="font-size: 13px; margin-right: 6px;">{m["icon"]}</span><span style="font-size: 11px; color: {m["cor"]}; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">{m["nome"]}</span></div>'

    st.markdown(
        f"""
    <div style="display: flex; align-items: center; background: rgba(255,255,255,0.02); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); border-left: 5px solid {COR_PRINCIPAL}; box-shadow: 0 8px 16px rgba(0,0,0,0.2); margin-bottom: 30px; flex-wrap: wrap; gap: 20px;">
        <img src="{url_foto_header}" style="width: 85px; height: 85px; border-radius: 50%; border: 2px solid {COR_PRINCIPAL}; object-fit: cover; box-shadow: 0 0 10px rgba(255,122,0,0.2);">
        <div style="flex: 1; min-width: 200px;">
            <h2 style="margin: 0; color: white; font-size: 22px; font-weight: 700;">{user_nome_exibicao}</h2>
            <p style="margin: 4px 0 12px 0; color: {COR_TEXTO}; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">{dept_usuario} • {nivel}</p>
            <div style="display: flex; flex-wrap: wrap;">{html_badges_topo if html_badges_topo else f'<span style="color:#555; font-size:12px; font-style:italic;">Conquiste metas para desbloquear medalhas no topo do perfil</span>'}</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ==========================================================
    # 🏆 VITRINE DE TROFÉUS ABERTA (ESTILO SHOWROOM)
    # ==========================================================
    st.markdown("### 🏆 Galeria de Conquistas e Medalhas")
    st.caption(
        "Acompanhe seus desafios mensais e marcos históricos no sistema de qualidade."
    )
    st.write("##")

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    for idx, (m_id, m_dados) in enumerate(todas_medalhas.items()):
        conq = m_id in medalhas_desbloqueadas

        html_box = f"""
        <div style="background: {f'linear-gradient(145deg, {m_dados["cor"]}08, rgba(0,0,0,0))' if conq else 'rgba(255,255,255,0.01)'}; border: 1px solid {m_dados['cor'] if conq else 'rgba(255,255,255,0.05)'}; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: {f'0 4px 15px {m_dados["cor"]}10' if conq else 'none'}; opacity: {1 if conq else 0.4}; transition: all 0.2s;">
            <div style="font-size: 38px; margin-bottom: 10px; filter: {f'drop-shadow(0 0 8px {m_dados["cor"]}50)' if conq else 'none'};">{m_dados['icon'] if conq else '🔒'}</div>
            <div style="font-weight: 700; font-size: 14px; color: #fff; letter-spacing: 0.3px;">{m_dados['nome']}</div>
            <div style="font-size: 12px; color: {COR_TEXTO}; margin-top: 6px; line-height: 1.3; min-height: 32px; display: flex; align-items: center;">{m_dados['desc']}</div>
            <div style="background-color: {m_dados['cor'] if conq else '#333'}20; color: {m_dados['cor'] if conq else '#666'}; padding: 2px 8px; border-radius: 10px; font-size: 9px; margin-top: 12px; font-weight: 900; letter-spacing: 1px; border: 1px solid {m_dados['cor'] if conq else '#444'}40;">{m_dados['tipo']}</div>
        </div>
        """
        with cols[idx % 3]:
            st.markdown(html_box, unsafe_allow_html=True)

    st.write("##")
    st.divider()

    # ==========================================================
    # ⚙️ CONFIGURAÇÕES (FOTO COM PREVIEW E SENHA FIX)
    # ==========================================================
    st.markdown("### ⚙️ Configurações da Conta")
    st.caption("Personalize sua identificação e mantenha seu acesso seguro.")
    st.write("##")

    c_foto, c_senha = st.columns(2)

    # ALTURA FIXA: Ambos os cartões terão exatamente 480px de altura para alinhamento perfeito.
    ALTURA_CAIXAS = 480

    with c_foto:
        with st.container(height=ALTURA_CAIXAS, border=True):
            st.markdown(
                f"<h4 style='color: {COR_PRINCIPAL};'>🖼️ Alterar Foto de Perfil</h4>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='font-size: 13px; color: #888;'>Envie um arquivo quadrado (JPG/PNG).</p>",
                unsafe_allow_html=True,
            )
            st.write("")

            novo_arquivo = st.file_uploader(
                "Selecione uma foto:",
                type=["png", "jpg", "jpeg"],
                key="perfil_uploader",
                label_visibility="collapsed",
            )

            if novo_arquivo:
                st.write("")
                st.markdown("**Prévia da Foto:**")
                st.image(novo_arquivo, width=110)
                st.write("")

                if st.button(
                    "✅ Confirmar e Salvar Foto",
                    use_container_width=True,
                    type="primary",
                ):
                    with st.spinner("Salvando na nuvem..."):
                        try:
                            ext = novo_arquivo.name.split(".")[-1]
                            nome_climb = str(user_login)
                            nome_arq = (
                                limpar_nome_arquivo(nome_climb.split("@")[0])
                                + f".{ext}"
                            )

                            supabase.storage.from_("avatars").upload(  # type: ignore
                                path=nome_arq,
                                file=novo_arquivo.getvalue(),
                                file_options={
                                    "upsert": "true",
                                    "content-type": f"image/{ext}",
                                },
                            )
                            url = supabase.storage.from_("avatars").get_public_url(nome_arq)  # type: ignore
                            supabase.table("usuarios").update({"foto_url": url}).eq("id", meu_id).execute()  # type: ignore

                            # 👇 Inserida a Auditoria aqui
                            registrar_auditoria(
                                "ALTERAÇÃO DE PERFIL", 
                                "Usuário atualizou a própria foto de perfil.", 
                                user_nome_exibicao, 
                                user_nome_exibicao
                            )

                            st.session_state["foto_url"] = url
                            st.success("Foto de perfil atualizada!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    with c_senha:
        with st.container(height=ALTURA_CAIXAS, border=True):
            st.markdown(
                f"<h4 style='color: {COR_PRINCIPAL};'>🔐 Alterar Senha de Acesso</h4>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='font-size: 13px; color: #888;'>Mantenha suas credenciais sempre seguras.</p>",
                unsafe_allow_html=True,
            )
            st.write("")

            # BORDER=FALSE: Remove a borda dupla do formulário!
            with st.form("form_senha_perfil_final", clear_on_submit=True, border=False):
                s_at = st.text_input("Senha Atual", type="password")
                s_nv = st.text_input("Nova Senha", type="password")
                s_cf = st.text_input("Confirmar Nova Senha", type="password")

                st.write("")
                btn_save = st.form_submit_button(
                    "Atualizar Senha", use_container_width=True, type="primary"
                )

                if btn_save:
                    if s_nv != s_cf:
                        st.error("As novas senhas digitadas não coincidem.")
                    elif len(s_nv) < 4:
                        st.error("A nova senha deve possuir pelo menos 4 caracteres.")
                    else:
                        h_dig = hash_password(s_at)
                        if h_dig == senha_banco or s_at.strip() == senha_banco:
                            supabase.table("usuarios").update({"senha": hash_password(s_nv)}).eq("id", meu_id).execute()  # type: ignore
                            
                            # 👇 Inserida a Auditoria aqui
                            registrar_auditoria(
                                "ALTERAÇÃO DE SENHA", 
                                "Usuário alterou a própria senha de acesso via painel.", 
                                user_nome_exibicao, 
                                user_nome_exibicao
                            )
                            
                            st.success("Sua senha de acesso foi modificada!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("A senha atual informada está incorreta.")