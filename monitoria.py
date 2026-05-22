import streamlit as st
import pandas as pd
import time
import uuid
import pytz
from datetime import datetime
from database import salvar_monitoria_auditada, supabase, get_all_records_db

# --- IMPORT DA IA AQUI ---
from analise_ia import sugerir_pdi_ia

# -------------------------


# ===================================================================
# 🎨 FUNÇÃO DO MODAL FLUTUANTE (DETALHES DA MONITORIA NO HISTÓRICO)
# ===================================================================
@st.dialog("📊 Detalhes da Avaliação", width="large")
def modal_detalhes_monitoria(row, foto_sdr, foto_auditor):

    auditor_nome = row.get("monitor_responsavel", "Sistema")
    sdr_nome = row.get("sdr", "Colaborador")
    nota = int(float(str(row.get("nota", 0))))
    data_formatada = (
        row["criado_em"].strftime("%d/%m/%Y às %H:%M")
        if pd.notna(row.get("criado_em"))
        else "Data N/D"
    )

    # CABEÇALHO DO MODAL
    c_img_aud, c_img_sdr, c_info, c_nota = st.columns([1, 1, 3, 1.5])
    with c_img_sdr:
        if foto_sdr:
            st.markdown(
                f'<div style="text-align:center;"><img src="{foto_sdr}" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #1f77b4;"><br><small>SDR</small></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align:center; font-size: 40px;">👤<br><small>SDR</small></div>',
                unsafe_allow_html=True,
            )

    with c_img_aud:
        if foto_auditor:
            st.markdown(
                f'<div style="text-align:center;"><img src="{foto_auditor}" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #ccc;"><br><small>Auditor</small></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align:center; font-size: 40px;">🕵️<br><small>QA</small></div>',
                unsafe_allow_html=True,
            )

    with c_info:
        st.markdown(f"#### Avaliado: {sdr_nome}")
        st.caption(f"📅 Aplicada em: {data_formatada} | 🕵️ {auditor_nome}")

    with c_nota:
        cor_nota = "#00cc96" if nota >= 90 else "#ff4b4b"
        st.markdown(
            f"""
            <div style='text-align: right;'>
                <span style='font-size: 14px; color: #888;'>Nota Final</span><br>
                <span style='font-size: 34px; font-weight: bold; color: {cor_nota};'>{nota}%</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.divider()

    # CORPO DO MODAL (2 COLUNAS)
    c_esq, c_dir = st.columns([1.2, 1])

    with c_esq:
        st.markdown("#### 💬 Feedback do Auditor")
        obs = row.get("observacoes", "")
        if pd.notna(obs) and obs.strip():
            with st.chat_message("assistant"):
                st.write(obs)
        else:
            st.info("Nenhum comentário geral registrado.")

        st.write("---")
        st.markdown("#### 🔗 Links da Avaliação")
        col_b1, col_b2 = st.columns(2)
        if pd.notna(row.get("link_selene")) and str(row.get("link_selene")).strip():
            col_b1.link_button(
                "🎧 Gravação (Selene)", url=row["link_selene"], use_container_width=True
            )
        if pd.notna(row.get("link_nectar")) and str(row.get("link_nectar")).strip():
            col_b2.link_button(
                "🗂️ CRM (Nectar)", url=row["link_nectar"], use_container_width=True
            )

    with c_dir:
        st.markdown("#### 🚨 Pontos Descontados")
        detalhes = row.get("detalhes", {})
        erros_encontrados = 0

        if isinstance(detalhes, dict):
            for item, info in detalhes.items():
                if isinstance(info, dict):
                    n = info.get("nota", "C")
                    if n in ["NC", "NGC", "NC Grave"]:
                        erros_encontrados += 1

                        peso_desc = info.get("peso", info.get("valor", "?"))
                        cor_badge = (
                            "#ff4b4b"
                            if n == "NGC"
                            else ("#ff9900" if n == "NC Grave" else "#f2c500")
                        )
                        comentario = info.get("comentario", "Sem justificativa")

                        html_erro = f"""
                        <div style="padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; margin-bottom: 10px; background-color: rgba(0,0,0,0.1);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                                <strong style="font-size: 14px;">❌ {item}</strong>
                            </div>
                            <div style="margin-bottom: 8px;">
                                <span style="background-color: {cor_badge}; color: #fff; padding: 2px 6px; border-radius: 12px; font-size: 11px; font-weight: bold;">{n}</span>
                                <span style="background-color: #444; color: #fff; padding: 2px 6px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-left: 4px;">-{peso_desc} pts</span>
                            </div>
                            <div style="font-size: 13px; font-style: italic; color: #aaa;">"{comentario}"</div>
                        </div>
                        """
                        st.markdown(html_erro, unsafe_allow_html=True)

                        if info.get("evidencia_anexada"):
                            url_img = info.get("url_arquivo")
                            if url_img:
                                st.page_link(
                                    url_img, label="Ver Evidência Anexada", icon="🖼️"
                                )

        if erros_encontrados == 0:
            st.success(
                "✨ Avaliação perfeita! Nenhum erro grave foi registrado nesta monitoria."
            )


# ===================================================================
# 🚀 RENDERIZAÇÃO DA PÁGINA PRINCIPAL
# ===================================================================
def render_nova_monitoria():
    # --- TRAVA ANTI-PYLANCE ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados. Verifique suas credenciais.")
        return
    # ------------------------------------------------------------------

    dept_selecionado = st.session_state.get("departamento_selecionado", "Todos")
    nivel_logado = st.session_state.get("nivel", "USUARIO").upper()
    nome_completo_logado = st.session_state.get("user_nome", "")

    col_header, _ = st.columns([4, 1])
    with col_header:
        st.title("📝 Gestão de Monitorias")
        st.markdown(
            "Realize novas avaliações de qualidade ou consulte o histórico da equipe."
        )
    st.divider()

    # ==========================================================
    # 1. BUSCA DE CRITÉRIOS, USUÁRIOS E MONITORIAS
    # ==========================================================
    try:
        res_crit = supabase.table("criterios_qa").select("*").eq("esta_ativo", True).execute()  # type: ignore
        df_criterios = pd.DataFrame(res_crit.data) if res_crit.data else pd.DataFrame()

        # Busca todos os usuários sem filtro prévio para garantirmos a limpeza no Pandas
        res_users = supabase.table("usuarios").select("*").execute()  # type: ignore
        df_users = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame()

        df_monitorias = get_all_records_db("monitorias")
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return

    mapa_fotos = {}
    if not df_users.empty:
        for _, u in df_users.iterrows():
            mapa_fotos[u["nome"]] = u.get("foto_url", None)

    # ==========================================================
    # 🛡️ TRAVA DE SEGURANÇA BLINDADA (Filtro Duplo de Colunas)
    # ==========================================================
    if not df_users.empty:
        # LÓGICA DE DETECÇÃO DE INATIVOS (Olhando para as duas colunas: "esta_ativo" e "ativo")
        def checar_se_esta_ativo(row):
            v_esta_ativo = row.get("esta_ativo")
            v_ativo = row.get("ativo")

            def is_true(v):
                if pd.isna(v):
                    return None
                if isinstance(v, bool):
                    return v
                return str(v).strip().lower() in [
                    "true",
                    "1",
                    "sim",
                    "yes",
                    "t",
                    "y",
                    "ativo",
                ]

            t1 = is_true(v_esta_ativo)
            t2 = is_true(v_ativo)

            # Se QUALQUER UMA das colunas estiver explicitamente False, o usuário está inativo!
            if t1 is False or t2 is False:
                return False

            # Se pelo menos uma estiver True, ele é válido
            if t1 is True or t2 is True:
                return True

            return False  # Se ambas forem nulas, descartamos

        df_users["ativo_verificado"] = df_users.apply(checar_se_esta_ativo, axis=1)
        df_users = df_users[df_users["ativo_verificado"] == True].copy()

        # Filtro de Palavras-Chave (Caso alguém tenha escrito INATIVO no departamento/nível)
        df_users = df_users[
            (
                ~df_users["nivel"]
                .astype(str)
                .str.upper()
                .str.contains("INATIVO|DESLIGADO|DESATIVADO", na=False)
            )
            & (
                ~df_users["departamento"]
                .astype(str)
                .str.upper()
                .str.contains("INATIVO|DESLIGADO|DESATIVADO", na=False)
            )
        ].copy()

        # Elimina a conta ADMIN
        df_users = df_users[
            (df_users["nivel"].astype(str).str.upper() != "ADMIN")
            & (~df_users["nome"].astype(str).str.upper().isin(["ADMIN", "SISTEMA"]))
            & (
                ~df_users["email"]
                .astype(str)
                .str.contains("admin@", na=False, case=False)
            )
        ].copy()

    df_users_filtrado = df_users.copy()
    if not df_users_filtrado.empty and dept_selecionado != "Todos":
        dept_user = dept_selecionado.strip().upper()
        df_users_filtrado = df_users_filtrado[
            (
                df_users_filtrado["departamento"].astype(str).str.strip().str.upper()
                == dept_user
            )
            | (
                df_users_filtrado["nivel"].astype(str).str.strip().str.upper()
                == dept_user
            )
        ]

    lista_colaboradores = (
        sorted(df_users_filtrado["nome"].dropna().unique().tolist())
        if not df_users_filtrado.empty
        else []
    )
    opcoes_sdr = ["Selecione..."] + lista_colaboradores

    # ==========================================================
    # 2. SISTEMA DE ABAS (TABS)
    # ==========================================================
    aba_nova, aba_historico = st.tabs(
        ["📝 Realizar Avaliação", "📚 Histórico de Monitorias"]
    )

    # ----------------------------------------------------------
    # ABA 1: NOVA MONITORIA (O FORMULÁRIO DE AVALIAÇÃO)
    # ----------------------------------------------------------
    with aba_nova:
        if nivel_logado not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            st.warning(
                "⚠️ Você não tem permissão para realizar avaliações. Acesse a aba 'Histórico' para ver suas notas."
            )
        else:
            with st.container(border=True):
                st.markdown("### 👤 Identificação da Chamada")
                c1, c2, c3 = st.columns([2, 1.5, 1.5])

                sdr_escolhido = c1.selectbox("Colaborador Auditado", options=opcoes_sdr)
                link_selene = c2.text_input(
                    "URL da Gravação (Selene/Zoom)", placeholder="http://..."
                )
                link_nectar = c3.text_input(
                    "URL do CRM (Nectar)", placeholder="http://..."
                )

            if sdr_escolhido == "Selecione...":
                st.info(
                    "👆 Selecione um colaborador acima para carregar o checklist correspondente."
                )
            else:
                dept_do_colaborador = "Todos"
                if not df_users.empty:
                    linha_colab = df_users[df_users["nome"] == sdr_escolhido]
                    if not linha_colab.empty:
                        dept_do_colaborador = str(
                            linha_colab.iloc[0].get("departamento", "Todos")
                        ).strip()

                st.markdown(f"**Setor do Colaborador:** `{dept_do_colaborador}`")

                df_crit_filtrado = pd.DataFrame()
                if not df_criterios.empty:
                    df_crit_filtrado = df_criterios[
                        (
                            df_criterios["departamento"]
                            .astype(str)
                            .str.strip()
                            .str.upper()
                            == dept_do_colaborador.upper()
                        )
                        | (
                            df_criterios["departamento"]
                            .astype(str)
                            .str.strip()
                            .str.title()
                            == "Todos"
                        )
                    ].copy()

                # --- FORMULÁRIO BLINDADO E REDESENHADO ---
                with st.form("form_monitoria_v8", clear_on_submit=False):
                    st.markdown("### ✅ Checklist de Qualidade")

                    respostas = {}

                    # PREVINE QUEBRA DO TABS SE NÃO HOUVER GRUPOS
                    if (
                        not df_crit_filtrado.empty
                        and "grupo" in df_crit_filtrado.columns
                    ):
                        grupos_brutos = (
                            df_crit_filtrado["grupo"].dropna().unique().tolist()
                        )
                        grupos = [g for g in grupos_brutos if str(g).strip()]
                        if not grupos:
                            grupos = ["Geral"]
                    else:
                        grupos = ["Geral"]

                    # =======================================================
                    # ✨ NOVO DESIGN: ABAS DE CATEGORIA NO LUGAR DE EXPANDERS
                    # =======================================================
                    abas_grupos = st.tabs([f"📂 {str(g).upper()}" for g in grupos])

                    for idx, grupo in enumerate(grupos):
                        with abas_grupos[idx]:
                            st.write("##")  # Espaçamento respirável

                            if not df_crit_filtrado.empty:
                                itens_grupo = df_crit_filtrado[
                                    df_crit_filtrado["grupo"] == grupo
                                ]
                            else:
                                itens_grupo = pd.DataFrame()

                            if itens_grupo.empty:
                                st.info(
                                    "Nenhum critério cadastrado para este departamento."
                                )

                            for _, row in itens_grupo.iterrows():
                                id_c = row["id"]
                                nome_c = row["nome"]
                                peso_c = int(row.get("peso", 1))
                                eh_fatal = bool(row.get("eh_fatal", False))

                                # CARD INDIVIDUAL PARA CADA PERGUNTA
                                with st.container(border=True):
                                    # Título Estilizado com HTML
                                    html_title = f"""
                                    <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;'>
                                        <strong style='font-size: 15px; color: #eee;'>{nome_c}</strong>
                                        <span style='background-color: #333; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px;'>Peso: {peso_c} pts</span>
                                        {'<span style="background-color: #ff4b4b; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;">🚨 FATAL</span>' if eh_fatal else ''}
                                    </div>
                                    """
                                    st.markdown(html_title, unsafe_allow_html=True)

                                    # Linha de Inputs alinhada
                                    col_res, col_com, col_img = st.columns(
                                        [1.5, 2, 1.2]
                                    )
                                    v_res = col_res.radio(
                                        f"Status {id_c}",
                                        ["C", "NC", "NC Grave", "NSA"],
                                        index=0,
                                        horizontal=True,
                                        label_visibility="collapsed",
                                        key=f"rad_{id_c}",
                                    )
                                    v_com = col_com.text_input(
                                        "Comentário",
                                        placeholder="Justificativa se NC...",
                                        label_visibility="collapsed",
                                        key=f"com_{id_c}",
                                    )
                                    v_img = col_img.file_uploader(
                                        "Evidência",
                                        type=["png", "jpg", "jpeg"],
                                        label_visibility="collapsed",
                                        key=f"file_{id_c}",
                                    )

                                    respostas[nome_c] = {
                                        "valor": v_res,
                                        "peso": peso_c,
                                        "eh_fatal": eh_fatal,
                                        "comentario": v_com,
                                        "arquivo": v_img,
                                        "nome_original": v_img.name if v_img else None,
                                    }

                    st.write("---")

                    # =======================================================
                    # SESSÃO FINAL DO FORMULÁRIO (CARD SEPARADO)
                    # =======================================================
                    with st.container(border=True):
                        st.markdown("### 🧠 Fechamento e PDI")
                        st.caption(
                            "Você pode usar a IA para gerar um rascunho de plano de ação baseado nas 'Não Conformidades' apontadas acima."
                        )

                        texto_inicial = st.session_state.get("feedback_sugerido", "")
                        observacoes = st.text_area(
                            "Pontos Positivos e Planos de Ação (Aparecerá para o SDR):",
                            value=texto_inicial,
                            height=180,
                        )

                    st.markdown("<br>", unsafe_allow_html=True)

                    # === BOTÕES ===
                    c_btn1, c_btn2 = st.columns(2)
                    btn_ia = c_btn1.form_submit_button(
                        "🤖 Sugerir PDI com IA (Rascunho)", use_container_width=True
                    )
                    btn_salvar = c_btn2.form_submit_button(
                        "🚀 Finalizar e Salvar Monitoria",
                        use_container_width=True,
                        type="primary",
                    )

                    # --- LÓGICA DE AÇÃO DOS BOTÕES ---
                    if btn_ia:
                        erros_para_ia = {
                            nome: item["comentario"]
                            for nome, item in respostas.items()
                            if item["valor"] in ["NC", "NC Grave"]
                        }
                        if not erros_para_ia:
                            st.info(
                                "✨ Nenhum erro marcado. A IA sugere enviar um feedback de parabéns!"
                            )
                            st.session_state["feedback_sugerido"] = (
                                f"Excelente atendimento, {sdr_escolhido}! Você seguiu os processos com perfeição. Parabéns pelo resultado e continue assim!"
                            )
                            st.rerun()
                        else:
                            with st.spinner(
                                "🧠 Lendo os erros e criando o plano de ação..."
                            ):
                                sugestao = sugerir_pdi_ia(
                                    erros_para_ia, dept_do_colaborador
                                )
                                st.session_state["feedback_sugerido"] = sugestao
                                st.rerun()

                    elif btn_salvar:
                        with st.spinner("Calculando nota e processando evidências..."):
                            total_maximo_ponderado = 0.0
                            total_conquistado_ponderado = 0.0
                            fatal_detectado = False
                            detalhes_finais = {}
                            erro_upload = False

                            for nome, item in respostas.items():
                                res = item["valor"]
                                peso = item["peso"]
                                fatal = item["eh_fatal"]

                                url_publica = None
                                if item["arquivo"]:
                                    try:
                                        f = item["arquivo"]
                                        ext = f.name.split(".")[-1].lower()
                                        nome_bucket = (
                                            f"prova_{uuid.uuid4().hex[:10]}.{ext}"
                                        )
                                        supabase.storage.from_("evidencias").upload(path=nome_bucket, file=f.getvalue(), file_options={"content-type": f.type})  # type: ignore

                                        res_url = supabase.storage.from_("evidencias").get_public_url(nome_bucket)  # type: ignore
                                        url_publica = (
                                            res_url
                                            if isinstance(res_url, str)
                                            else getattr(
                                                res_url, "public_url", str(res_url)
                                            )
                                        )

                                    except Exception as e:
                                        st.error(f"🛑 Erro no upload: {e}")
                                        erro_upload = True

                                if res != "NSA":
                                    total_maximo_ponderado += peso
                                    if res == "C":
                                        total_conquistado_ponderado += peso
                                    else:
                                        if fatal:
                                            fatal_detectado = True

                                if res == "NC Grave" or res == "NGC":
                                    fatal_detectado = True

                                detalhes_finais[nome] = {
                                    "nota": res,
                                    "comentario": item["comentario"],
                                    "peso_aplicado": peso,
                                    "foi_fatal": fatal,
                                    "url_arquivo": url_publica,
                                    "evidencia_anexada": True if url_publica else False,
                                    "arquivo": item["nome_original"],
                                }

                            if erro_upload:
                                st.stop()

                            nota_final = (
                                0
                                if fatal_detectado
                                else (
                                    (
                                        total_conquistado_ponderado
                                        / total_maximo_ponderado
                                        * 100
                                    )
                                    if total_maximo_ponderado > 0
                                    else 100
                                )
                            )

                            payload = {
                                "sdr": sdr_escolhido,
                                "departamento": dept_do_colaborador,
                                "nota": int(round(nota_final)),
                                "link_selene": link_selene,
                                "link_nectar": link_nectar,
                                "observacoes": observacoes,
                                "monitor_responsavel": st.session_state.get(
                                    "user_nome", "Sistema"
                                ),
                                "detalhes": detalhes_finais,
                            }

                            sucesso, msg = salvar_monitoria_auditada(payload)

                            if sucesso:
                                if "feedback_sugerido" in st.session_state:
                                    del st.session_state["feedback_sugerido"]

                                st.success(
                                    f"✅ Monitoria salva com nota {payload['nota']}%!"
                                )

                                try:
                                    supabase.table("notificacoes").insert(
                                        {  # type: ignore
                                            "usuario": sdr_escolhido,
                                            "mensagem": f"📊 Você recebeu uma nova avaliação de qualidade! Nota: {payload['nota']}%.",
                                            "lida": False,
                                        }
                                    ).execute()

                                    if payload["nota"] == 100:
                                        res_historico = supabase.table("monitorias").select("nota").eq("sdr", sdr_escolhido).order("criado_em", desc=True).limit(3).execute()  # type: ignore

                                        ultimas_notas = []
                                        if hasattr(
                                            res_historico, "data"
                                        ) and isinstance(res_historico.data, list):
                                            for r in res_historico.data:  # type: ignore
                                                if isinstance(r, dict):
                                                    try:
                                                        nota_limpa = float(
                                                            str(r.get("nota", 0))
                                                        )
                                                        ultimas_notas.append(nota_limpa)
                                                    except:
                                                        pass

                                        if len(ultimas_notas) == 3 and all(
                                            n == 100.0 for n in ultimas_notas
                                        ):
                                            msg_medalha = "🔥 ON FIRE! Absoluto! Você conquistou 3 monitorias seguidas com nota 100%!"
                                        else:
                                            msg_medalha = "🎯 PARABÉNS! Você conquistou a Medalha Sniper (Nota 100%)."

                                        supabase.table("notificacoes").insert({"usuario": sdr_escolhido, "mensagem": msg_medalha, "lida": False}).execute()  # type: ignore

                                    elif not fatal_detectado and payload["nota"] > 0:
                                        supabase.table("notificacoes").insert(
                                            {  # type: ignore
                                                "usuario": sdr_escolhido,
                                                "mensagem": f"🛡️ Ótimo trabalho! Você finalizou uma call sem erros Fatais (Medalha Muralha).",
                                                "lida": False,
                                            }
                                        ).execute()
                                except Exception as e:
                                    print(f"Erro silencioso ao gerar notificação: {e}")

                                if fatal_detectado:
                                    st.error(
                                        "🚨 NOTA ZERO: Um item Crítico/Fatal foi descumprido."
                                    )

                                st.balloons()
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(f"Erro ao salvar: {msg}")

    # ----------------------------------------------------------
    # ABA 2: HISTÓRICO DE MONITORIAS (SISTEMA DE GRID PREMIUM)
    # ----------------------------------------------------------
    with aba_historico:
        if df_monitorias is None or df_monitorias.empty:
            st.info("Nenhuma monitoria registrada ainda.")
            return

        fuso = pytz.timezone("America/Sao_Paulo")
        df_historico = df_monitorias.copy()
        df_historico["criado_em"] = pd.to_datetime(
            df_historico["criado_em"], errors="coerce"
        )
        if not df_historico["criado_em"].isna().all():
            if df_historico["criado_em"].dt.tz is None:
                df_historico["criado_em"] = (
                    df_historico["criado_em"].dt.tz_localize("UTC").dt.tz_convert(fuso)
                )
            else:
                df_historico["criado_em"] = df_historico["criado_em"].dt.tz_convert(
                    fuso
                )

        df_historico = df_historico.sort_values(by="criado_em", ascending=False)

        if dept_selecionado != "Todos" and "departamento" in df_historico.columns:
            df_historico = df_historico[
                df_historico["departamento"].astype(str).str.strip().str.upper()
                == dept_selecionado.strip().upper()
            ]

        if nivel_logado not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            df_historico = df_historico[
                df_historico["sdr"].astype(str).str.strip().str.upper()
                == nome_completo_logado.strip().upper()
            ]
        elif nivel_logado == "AUDITOR":
            df_historico = df_historico[
                df_historico["monitor_responsavel"].astype(str).str.strip().str.upper()
                == nome_completo_logado.strip().upper()
            ]

        # ==========================================================
        # 🔍 NOVO CAMPO DE BUSCA INTELIGENTE
        # ==========================================================
        termo_busca = st.text_input(
            "🔍 Buscar no histórico:",
            placeholder="Digite o nome do SDR ou do Avaliador...",
        )

        if termo_busca:
            df_historico = df_historico[
                df_historico["sdr"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
                | df_historico["monitor_responsavel"]
                .astype(str)
                .str.contains(termo_busca, case=False, na=False)
            ]

        if df_historico.empty:
            st.warning("⚠️ Nenhum histórico encontrado com esses filtros/busca.")
        else:
            st.markdown(f"Exibindo **{len(df_historico)}** avaliações.")
            st.write("---")

            # SISTEMA DE GRADE (GRID 3x3)
            NUM_COLS = 3
            cols = st.columns(NUM_COLS)

            for i, (_, row) in enumerate(df_historico.iterrows()):
                sdr_nome = row.get("sdr", "Desconhecido")
                auditor_nome = row.get("monitor_responsavel", "Sistema")
                nota = int(float(str(row.get("nota", 0))))
                data_dt = row.get("criado_em")
                data_str = (
                    data_dt.strftime("%d/%m/%Y") if pd.notna(data_dt) else "Data N/D"
                )

                foto_sdr = mapa_fotos.get(sdr_nome, None)
                foto_auditor = mapa_fotos.get(auditor_nome, None)

                with cols[i % NUM_COLS]:
                    with st.container(border=True):
                        c_img, c_txt = st.columns([1, 2.5])
                        with c_img:
                            if foto_sdr:
                                st.markdown(
                                    f'<img src="{foto_sdr}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid {"#00cc96" if nota>=90 else "#ff4b4b"}; margin-top: 5px;">',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    '<div style="font-size: 40px; margin-top: -5px;">👤</div>',
                                    unsafe_allow_html=True,
                                )
                        with c_txt:
                            st.markdown(f"**{sdr_nome}**")
                            st.caption(f"📅 {data_str}")

                        st.divider()

                        cor_nota = "#00cc96" if nota >= 90 else "#ff4b4b"
                        st.markdown(
                            f"""
                            <div style='text-align: center; margin-bottom: 5px;'>
                                <span style='font-size: 13px; color: #888;'>Nota de Qualidade</span><br>
                                <span style='font-size: 36px; font-weight: bold; color: {cor_nota};'>{nota}%</span>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<div style='text-align: center; font-size: 12px; color: #aaa; margin-bottom: 15px;'>🕵️ Avaliado por: {auditor_nome}</div>",
                            unsafe_allow_html=True,
                        )

                        if st.button(
                            "🔍 Ver Detalhes",
                            type="secondary",
                            use_container_width=True,
                            key=f"btn_hist_{row['id']}",
                        ):
                            modal_detalhes_monitoria(row, foto_sdr, foto_auditor)
