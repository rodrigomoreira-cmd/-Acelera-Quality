import streamlit as st
import pandas as pd
import time
import pytz
import copy
from datetime import datetime
from database import supabase, get_all_records_db, registrar_auditoria

# --- IMPORT DA IA AQUI ---
from analise_ia import analisar_sentimento_texto

# -------------------------


# ===================================================================
# 🎨 1. MODAL DO COLABORADOR (ABRIR CONTESTAÇÃO)
# ===================================================================
@st.dialog("📝 Abrir Nova Contestação", width="large")
def modal_abrir_contestacao(mon_row, id_sel, auditor_nome, foto_auditor, nome_completo):
    # --- BLINDAGEM PYLANCE PARA O MODAL ---
    if supabase is None:
        st.error("Erro interno: Banco de dados desconectado.")
        return
    # --------------------------------------

    # --- CARD DE DETALHES DA AVALIAÇÃO ---
    with st.container(border=True):
        c_foto, c_info, c_nota = st.columns([1, 2, 1])

        with c_foto:
            if foto_auditor:
                st.markdown(
                    f'<img src="{foto_auditor}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px solid #ccc;">',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="font-size: 60px;">🕵️</div>', unsafe_allow_html=True
                )

        with c_info:
            st.markdown(f"**Avaliador:** {auditor_nome}")
            dt_formatada = (
                mon_row["criado_em"].strftime("%d/%m/%Y às %H:%M")
                if pd.notna(mon_row["criado_em"])
                else "N/D"
            )
            st.caption(f"Aplicada em: {dt_formatada}")

        with c_nota:
            st.metric(label="Nota Final", value=f"{mon_row['nota']}%")

        obs = mon_row.get("observacoes", "")
        if pd.notna(obs) and obs.strip():
            st.divider()
            st.markdown("**💬 Comentário Geral do Auditor:**")
            st.info(f"_{obs}_")

    # --- SEÇÃO: ERROS ENCONTRADOS (LARGURA TOTAL) ---
    detalhes = mon_row.get("detalhes", {})
    erros_encontrados = 0

    st.markdown("#### 🚨 Pontos Descontados")

    if detalhes and isinstance(detalhes, dict):
        for item, info in detalhes.items():
            if isinstance(info, dict):
                n = info.get("nota", "")
                if n in ["NC", "NGC", "NC Grave"]:
                    erros_encontrados += 1

                    cor_badge = (
                        "#ff4b4b"
                        if n == "NGC"
                        else ("#ff9900" if n == "NC Grave" else "#f2c500")
                    )
                    comentario = info.get(
                        "comentario", "Nenhuma justificativa fornecida pelo auditor."
                    )

                    html_erro = f"""
                    <div style="padding: 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; margin-bottom: 15px; background-color: rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                            <strong style="font-size: 15px; display: flex; align-items: center; gap: 6px;">❌ {item}</strong>
                            <div>
                                <span style="background-color: {cor_badge}; color: #fff; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{n}</span>
                            </div>
                        </div>
                        <div style="font-size: 14px; font-style: italic; color: #aaa; margin-top: 5px;">"{comentario}"</div>
                    </div>
                    """
                    st.markdown(html_erro, unsafe_allow_html=True)

                    if info.get("evidencia_anexada"):
                        url_imagem = info.get("url_arquivo")
                        if url_imagem:
                            with st.expander("🖼️ Ver Evidência Anexada"):
                                st.image(url_imagem, use_container_width=True)

    if erros_encontrados == 0:
        st.success("✨ Nenhum erro grave detalhado nesta monitoria.")

    # --- SEÇÃO: FORMULÁRIO DE DEFESA ---
    st.divider()
    st.markdown("#### ✍️ Sua Defesa")
    st.caption(
        "Explique de forma clara o motivo da sua discordância. Se houver gravação, cite os minutos exatos."
    )

    motivo_sdr = st.text_area(
        "Justificativa (Obrigatório):",
        height=150,
        placeholder="Ex: Acredito que o apontamento de NGC não procede, pois no minuto 02:15 da ligação eu realizei a etapa...",
        key=f"txt_motivo_{id_sel}",
    )

    if st.button(
        "🚀 Enviar Defesa",
        type="primary",
        use_container_width=True,
        key=f"btn_enviar_{id_sel}",
    ):
        if not motivo_sdr or len(motivo_sdr) < 10:
            st.error("⚠️ Escreva uma justificativa clara (mínimo de 10 caracteres).")
        else:
            try:
                with st.spinner("🤖 Analisando argumentos com IA..."):
                    sent_ia, res_ia = analisar_sentimento_texto(motivo_sdr)

                payload = {
                    "monitoria_id": id_sel,
                    "motivo": motivo_sdr,
                    "status": "Pendente",
                    "resposta_admin": "",
                    "visualizada": False,
                    "sentimento_ia": sent_ia,
                    "resumo_ia": res_ia,
                    "sdr_nome": nome_completo,
                }

                supabase.table("contestacoes").insert(payload).execute()
                
                # 👇 CORREÇÃO NA AUDITORIA (Passando os 4 parâmetros corretamente)
                registrar_auditoria(
                    "ABERTURA DE CONTESTAÇÃO",
                    f"Abriu contestação para a avaliação de {auditor_nome}.",
                    nome_completo,     # Quem foi afetado (o próprio SDR)
                    nome_completo      # Quem fez a ação (o próprio SDR)
                )

                try:
                    supabase.table("notificacoes").insert(
                        {
                            "usuario": auditor_nome,
                            "mensagem": f"⚖️ {nome_completo} abriu um ticket de contestação referente à sua avaliação.",
                            "lida": False,
                        }
                    ).execute()
                except:
                    pass

                st.success("✅ Defesa enviada com sucesso para a equipe de qualidade!")
                time.sleep(1.5)
                get_all_records_db.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")


# ===================================================================
# 🎨 2. MODAL DA LIDERANÇA (JULGAR CONTESTAÇÃO)
# ===================================================================
@st.dialog("⚖️ Análise de Ticket de Contestação", width="large")
def modal_julgamento(
    row,
    id_cont_limpo,
    nota_limpa,
    auditor_original,
    nome_colaborador,
    data_formatada,
    tag_ia,
    resumo_ia,
    mapa_pesos,
):
    # --- BLINDAGEM PYLANCE PARA O MODAL ---
    if supabase is None:
        st.error("Erro interno: Banco de dados desconectado.")
        return
    # --------------------------------------
    
    # Resgata o nome de quem está julgando
    admin_logado = str(st.session_state.get('user_nome', 'Admin'))

    # -------------------------------------------------------------
    # 1. SEÇÃO DE ARGUMENTO (LARGURA TOTAL EM PILHA)
    # -------------------------------------------------------------
    st.markdown("#### 💬 Argumento do Colaborador")
    st.caption(f"Enviado em {data_formatada}")

    with st.chat_message("user"):
        st.write(row["motivo"])

    if pd.notna(resumo_ia) and str(resumo_ia).strip() != "":
        st.caption(f"🧠 **Resumo IA ({tag_ia}):** _{resumo_ia}_")

    st.write("---")

    # -------------------------------------------------------------
    # 2. SEÇÃO DE LINKS
    # -------------------------------------------------------------
    st.markdown("#### 🔗 Links da Avaliação")
    col_b1, col_b2 = st.columns(2)
    if pd.notna(row.get("link_selene")):
        col_b1.link_button(
            "🎧 Gravação (Selene)", url=row["link_selene"], use_container_width=True
        )
    if pd.notna(row.get("link_nectar")):
        col_b2.link_button(
            "🗂️ CRM (Nectar)", url=row["link_nectar"], use_container_width=True
        )

    st.write("---")

    # -------------------------------------------------------------
    # 3. SEÇÃO DE ERROS DESCONTADOS (LARGURA TOTAL EM PILHA)
    # -------------------------------------------------------------
    st.markdown("#### 🚨 Erros Descontados Originalmente")
    det_auditor = row.get("detalhes", {})
    erros_originais = []

    if isinstance(det_auditor, dict):
        for item, d_info in det_auditor.items():
            if isinstance(d_info, dict) and d_info.get("nota") in [
                "NC",
                "NGC",
                "NC Grave",
            ]:
                erros_originais.append(item)

                n = d_info.get("nota", "NC")
                peso_real = mapa_pesos.get(item.strip(), 0)

                cor_badge = (
                    "#ff4b4b"
                    if n == "NGC"
                    else ("#ff9900" if n == "NC Grave" else "#f2c500")
                )
                comentario = d_info.get("comentario", "Sem justificativa")

                html_erro = f"""
                <div style="padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; margin-bottom: 10px; background-color: rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <strong style="font-size: 14px;">❌ {item}</strong>
                    </div>
                    <div style="margin-bottom: 8px;">
                        <span style="background-color: {cor_badge}; color: #fff; padding: 2px 6px; border-radius: 12px; font-size: 11px; font-weight: bold;">{n}</span>
                        <span style="background-color: #444; color: #fff; padding: 2px 6px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-left: 4px;">-{peso_real} pts</span>
                    </div>
                    <div style="font-size: 13px; font-style: italic; color: #aaa;">"{comentario}"</div>
                </div>
                """
                st.markdown(html_erro, unsafe_allow_html=True)

                if d_info.get("evidencia_anexada"):
                    url_imagem = d_info.get("url_arquivo")
                    if url_imagem:
                        st.page_link(
                            url_imagem, label="Ver Evidência Anexada", icon="🖼️"
                        )

    st.divider()

    # -------------------------------------------------------------
    # 4. PAINEL DE JULGAMENTO (TOGGLES E NOTA AO VIVO)
    # -------------------------------------------------------------
    st.markdown("### ⚖️ Julgamento Oficial")

    decisao = st.radio(
        "Qual é o seu veredito final?",
        ["Aceita", "Recusada"],
        horizontal=True,
        key=f"modal_decisao_{id_cont_limpo}",
    )

    itens_perdoados = []
    nova_nota_final = nota_limpa

    if decisao == "Aceita":
        st.info(
            "ℹ️ **Ative a chave** ao lado dos itens que o SDR acertou. A nota será atualizada ao vivo na caixa verde abaixo!"
        )

        for idx, item in enumerate(erros_originais):
            info_op = det_auditor.get(item, {})
            tipo_op = info_op.get("nota", "NC")
            peso_real = mapa_pesos.get(item.strip(), 0)

            cor_badge = (
                "#ff4b4b"
                if tipo_op == "NGC"
                else ("#ff9900" if tipo_op == "NC Grave" else "#f2c500")
            )
            texto_recuperar = (
                "Recuperar Nota Máxima" if tipo_op == "NGC" else f"+{peso_real} pts"
            )

            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(
                        f"<div style='font-size: 14px; font-weight: 600; margin-bottom: 5px; color: #eee;'>{item}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span style='background-color: {cor_badge}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;'>{tipo_op}</span> <span style='color: #00cc66; font-weight: bold; font-size: 13px; margin-left: 8px;'>{texto_recuperar}</span>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.write("")
                    if st.toggle("Perdoar", key=f"tgl_perdoar_{id_cont_limpo}_{idx}"):
                        itens_perdoados.append(item)

        detalhes_simulados = (
            copy.deepcopy(det_auditor) if isinstance(det_auditor, dict) else {}
        )

        for item_perdoado in itens_perdoados:
            if item_perdoado in detalhes_simulados:
                detalhes_simulados[item_perdoado]["nota"] = "C (Revertido)"

        nota_recalculada = 100.0
        zerou_nota = False

        for item_nome, info_item in detalhes_simulados.items():
            if isinstance(info_item, dict):
                status_atual = info_item.get("nota", "C")
                if status_atual in ["NC", "NC Grave", "NGC"]:
                    if status_atual == "NGC":
                        zerou_nota = True
                    else:
                        peso_bd = mapa_pesos.get(item_nome.strip(), 0)
                        nota_recalculada -= peso_bd

        if zerou_nota:
            nova_nota_final = 0
        else:
            nova_nota_final = int(max(0, min(100, nota_recalculada)))

        pontos_recuperados = nova_nota_final - nota_limpa

        if pontos_recuperados > 0:
            st.success(
                f"🎯 **Nota Final Simulada:** de {nota_limpa}% passará para **{nova_nota_final}%** (+{pontos_recuperados} pontos)"
            )

    feedback = st.text_area(
        "Feedback Final para o Colaborador (Fica visível para o SDR):",
        height=100,
        placeholder="Explique sua decisão e oriente sobre o processo correto...",
        key=f"modal_feedback_{id_cont_limpo}",
    )

    if st.button(
        "🔨 Bater o Martelo e Salvar",
        type="primary",
        use_container_width=True,
        key=f"modal_btn_{id_cont_limpo}",
    ):
        try:
            supabase.table("contestacoes").update(
                {"status": decisao, "resposta_admin": feedback}
            ).eq("id", id_cont_limpo).execute()

            if decisao == "Aceita":
                supabase.table("monitorias").update(
                    {"nota": nova_nota_final, "detalhes": detalhes_simulados}
                ).eq("id", str(row["monitoria_id"])).execute()

                # 👇 CORREÇÃO NA AUDITORIA (Admin logado é o 4º parâmetro)
                registrar_auditoria(
                    "AJUSTE DE NOTA",
                    f"Nota recalculada de {nota_limpa}% para {nova_nota_final}% após defesa.",
                    nome_colaborador,
                    admin_logado
                )

            # 👇 CORREÇÃO NA AUDITORIA
            registrar_auditoria(
                "JULGAMENTO",
                f"A contestação de {nome_colaborador} foi julgada como '{decisao}'.",
                nome_colaborador,
                admin_logado
            )

            try:
                supabase.table("notificacoes").insert(
                    {
                        "usuario": nome_colaborador,
                        "mensagem": f"⚖️ Sua contestação foi julgada como: {decisao}. Verifique a aba de Contestações.",
                        "lida": False,
                    }
                ).execute()

                if decisao == "Aceita":
                    supabase.table("notificacoes").insert(
                        {
                            "usuario": nome_colaborador,
                            "mensagem": f"🎖️ PARABÉNS! Sua contestação foi aceita. Nova Nota Final: {nova_nota_final}%",
                            "lida": False,
                        }
                    ).execute()
            except:
                pass

            st.success(f"✅ Veredito salvo com sucesso!")
            time.sleep(1.5)
            get_all_records_db.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")


# ===================================================================
# 🚀 RENDERIZAÇÃO DA PÁGINA PRINCIPAL
# ===================================================================
def render_contestacao():

    # --- TRAVA ANTI-PYLANCE PRINCIPAL ---
    if supabase is None:
        st.error("Erro de conexão com o banco de dados. Verifique suas credenciais.")
        return
    # ------------------------------------------------------------------

    nivel = st.session_state.get("nivel", "USUARIO")
    nome_completo = st.session_state.get("user_nome", "")
    dept_selecionado = st.session_state.get("departamento_selecionado", "Todos")

    col_header, col_img = st.columns([4, 1])
    with col_header:
        st.title("⚖️ Central de Contestação")
        st.markdown("Bem-vindo ao canal oficial de revisão de auditorias da Qualidade.")
    st.divider()

    df_monitorias = get_all_records_db("monitorias")
    df_contestacoes = get_all_records_db("contestacoes")

    if df_monitorias is None or df_monitorias.empty:
        st.info("💡 Nenhuma monitoria encontrada no sistema.")
        return

    df_monitorias["id"] = df_monitorias["id"].astype(str).str.strip()
    df_monitorias["nota"] = (
        pd.to_numeric(df_monitorias["nota"], errors="coerce").fillna(0).astype(int)
    )

    fuso = pytz.timezone("America/Sao_Paulo")
    if "criado_em" in df_monitorias.columns:
        df_monitorias["criado_em"] = pd.to_datetime(
            df_monitorias["criado_em"], errors="coerce"
        )
        if not df_monitorias["criado_em"].isna().all():
            if df_monitorias["criado_em"].dt.tz is None:
                df_monitorias["criado_em"] = (
                    df_monitorias["criado_em"].dt.tz_localize("UTC").dt.tz_convert(fuso)
                )
            else:
                df_monitorias["criado_em"] = df_monitorias["criado_em"].dt.tz_convert(
                    fuso
                )

    if df_contestacoes is not None and not df_contestacoes.empty:
        df_contestacoes["id"] = df_contestacoes["id"].astype(str).str.strip()
        df_contestacoes["monitoria_id"] = (
            df_contestacoes["monitoria_id"].astype(str).str.strip()
        )

    # ==========================================================
    # 👤 VISÃO DO COLABORADOR (SDR / Especialista / Ingresso)
    # ==========================================================
    if nivel not in ["AUDITOR", "GESTAO", "ADMIN", "GERENCIA"]:

        st.info(
            "⏱️ **Regra de SLA:** Você possui até **3 dias corridos** após a data da avaliação para abrir uma contestação. Após este prazo, a nota é considerada validada."
        )
        st.write("##")

        minhas_monitorias = df_monitorias[
            df_monitorias["sdr"].astype(str).str.strip().str.upper()
            == nome_completo.strip().upper()
        ].copy()

        if minhas_monitorias.empty:
            st.success("🎉 Você ainda não possui monitorias registradas.")
            return

        hoje = datetime.now(fuso)
        minhas_monitorias["dias_passados"] = (
            hoje - minhas_monitorias["criado_em"]
        ).dt.days

        seus_ids_contestados = []
        if df_contestacoes is not None and not df_contestacoes.empty:
            coluna_nome = "sdr_nome" if "sdr_nome" in df_contestacoes.columns else "sdr"
            if coluna_nome in df_contestacoes.columns:
                seus_ids_contestados = df_contestacoes[
                    df_contestacoes[coluna_nome].astype(str).str.strip().str.upper()
                    == nome_completo.strip().upper()
                ]["monitoria_id"].tolist()

        disponiveis = minhas_monitorias[
            (~minhas_monitorias["id"].isin(seus_ids_contestados))
            & (minhas_monitorias["dias_passados"] <= 3)
        ]

        # --- SEÇÃO 1: AVALIAÇÕES DISPONÍVEIS ---
        st.markdown("### 📝 Avaliações Disponíveis")

        if disponiveis.empty:
            st.warning(
                "🔒 **Nenhuma avaliação disponível.** \nVocê já contestou as monitorias recentes ou elas passaram do prazo de 3 dias."
            )
        else:
            cols_sdr = st.columns(3)
            for i, (_, row) in enumerate(disponiveis.iterrows()):
                id_sel = row["id"]
                dias_restantes = 3 - row["dias_passados"]
                aviso_dias = (
                    "⏳ Último dia!"
                    if dias_restantes <= 0
                    else f"⏳ Restam {dias_restantes} dia(s)"
                )
                dt_format = (
                    row["criado_em"].strftime("%d/%m/%Y")
                    if pd.notna(row["criado_em"])
                    else "Data N/D"
                )
                auditor_nome = row["monitor_responsavel"]
                nota_sdr = row["nota"]

                with cols_sdr[i % 3]:
                    with st.container(border=True):
                        st.markdown(
                            f"<div style='font-size: 13px; color: #aaa;'>Avaliador: {auditor_nome}</div>",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"📅 {dt_format} | {aviso_dias}")

                        st.markdown(
                            f"""
                            <div style='text-align: center; margin: 10px 0;'>
                                <span style='font-size: 30px; font-weight: bold; color: {'#00cc96' if nota_sdr >= 90 else '#ff4b4b'};'>{nota_sdr}%</span>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        if st.button(
                            "📝 Contestar",
                            type="primary",
                            use_container_width=True,
                            key=f"btn_sdr_{id_sel}",
                        ):
                            try:
                                res_aud = (
                                    supabase.table("usuarios")
                                    .select("foto_url")
                                    .eq("nome", auditor_nome)
                                    .execute()
                                )
                                foto_auditor = None
                                if (
                                    hasattr(res_aud, "data")
                                    and isinstance(res_aud.data, list)
                                    and len(res_aud.data) > 0
                                ):
                                    if isinstance(res_aud.data[0], dict):
                                        foto_auditor = res_aud.data[0].get("foto_url")
                            except:
                                foto_auditor = None

                            modal_abrir_contestacao(
                                row, id_sel, auditor_nome, foto_auditor, nome_completo
                            )

        st.divider()

        # --- SEÇÃO 2: HISTÓRICO DE CONTESTAÇÕES ---
        st.markdown("### 📊 Seu Histórico")
        if df_contestacoes is not None and not df_contestacoes.empty:
            coluna_filtro = (
                "sdr_nome" if "sdr_nome" in df_contestacoes.columns else "sdr"
            )
            minhas_cont = df_contestacoes[
                df_contestacoes[coluna_filtro].astype(str).str.strip().str.upper()
                == nome_completo.strip().upper()
            ].copy()

            if not minhas_cont.empty:
                col_data_hist = (
                    "criado_em" if "criado_em" in minhas_cont.columns else "criado_em_x"
                )
                if col_data_hist in minhas_cont.columns:
                    minhas_cont[col_data_hist] = pd.to_datetime(
                        minhas_cont[col_data_hist], errors="coerce"
                    )
                    minhas_cont = minhas_cont.sort_values(
                        by=col_data_hist, ascending=False
                    )
                    minhas_cont["Data"] = (
                        minhas_cont[col_data_hist].dt.strftime("%d/%m/%Y").fillna("-")
                    )
                else:
                    minhas_cont["Data"] = "-"

                cols_hist = st.columns(3)
                for i, (_, hist) in enumerate(minhas_cont.iterrows()):
                    with cols_hist[i % 3]:
                        with st.container(border=True):
                            icone_status = "⏳"
                            if hist["status"] == "Aceita":
                                icone_status = "✅"
                            elif hist["status"] == "Recusada":
                                icone_status = "❌"

                            st.markdown(
                                f"**{icone_status} {hist['status']}** | 📅 {hist['Data']}"
                            )
                            st.caption(f"**Defesa:** {hist['motivo'][:60]}...")

                            if (
                                pd.notna(hist.get("resposta_admin"))
                                and str(hist["resposta_admin"]).strip() != ""
                            ):
                                with st.expander("Ler Feedback"):
                                    st.info(hist["resposta_admin"])
            else:
                st.info("Nenhuma contestação aberta no momento.")

    # ==========================================================
    # 🛡️ VISÃO DA LIDERANÇA (AUDITOR / GESTOR / ADMIN)
    # ==========================================================
    elif nivel in ["AUDITOR", "GESTAO", "ADMIN", "GERENCIA"]:
        st.markdown(f"🗂️ **Caixa de Entrada da Equipe:** `{dept_selecionado}`")
        st.write("##")

        df_criterios = get_all_records_db("criterios_qa")
        mapa_pesos = {}
        if df_criterios is not None and not df_criterios.empty:
            for _, row_crit in df_criterios.iterrows():
                nome_crit = str(row_crit.get("nome", "")).strip()
                peso_crit = pd.to_numeric(row_crit.get("peso", 0), errors="coerce")
                if pd.isna(peso_crit):
                    peso_crit = 0
                mapa_pesos[nome_crit] = int(peso_crit)

        if df_contestacoes is None or df_contestacoes.empty:
            st.success("🎉 Caixa de entrada vazia! Nenhuma contestação no momento.")
            return

        colunas_necessarias = [
            "id",
            "sdr",
            "departamento",
            "nota",
            "link_selene",
            "link_nectar",
            "detalhes",
            "monitor_responsavel",
        ]
        colunas_existentes = [
            c for c in colunas_necessarias if c in df_monitorias.columns
        ]

        df_completo = pd.merge(
            df_contestacoes,
            df_monitorias[colunas_existentes],
            left_on="monitoria_id",
            right_on="id",
            how="left",
        )

        if dept_selecionado != "Todos" and "departamento" in df_completo.columns:
            df_completo = df_completo[
                df_completo["departamento"].astype(str).str.strip().str.upper()
                == dept_selecionado.strip().upper()
            ]

        if nivel != "ADMIN":
            df_completo = df_completo[
                df_completo["monitor_responsavel"].astype(str).str.strip().str.upper()
                == nome_completo.strip().upper()
            ]

        pendentes = df_completo[df_completo["status"] == "Pendente"]

        if pendentes.empty:
            st.success(
                "✅ Tudo limpo! Não há tickets direcionados para você neste momento."
            )
        else:
            aba_p, aba_h = st.tabs(
                ["🔥 Requer Análise (Pendentes)", "📚 Histórico de Vereditos"]
            )

            with aba_p:
                st.markdown(
                    f"Você possui **{len(pendentes)}** contestações aguardando resposta."
                )
                st.write("---")

                NUM_COLS = 3
                cols = st.columns(NUM_COLS)

                for i, (_, row) in enumerate(pendentes.iterrows()):
                    id_cont_limpo = (
                        str(row["id_x"]) if "id_x" in row.index else str(row["id"])
                    )
                    nota_limpa = (
                        int(float(str(row["nota"]))) if pd.notna(row.get("nota")) else 0
                    )
                    auditor_original = row.get("monitor_responsavel", "Desconhecido")

                    nome_colaborador = "Desconhecido"
                    for campo in ["sdr_y", "sdr_x", "sdr", "sdr_nome"]:
                        if (
                            campo in row.index
                            and pd.notna(row[campo])
                            and str(row[campo]).strip().lower() != "none"
                        ):
                            nome_colaborador = str(row[campo])
                            break

                    data_raw = row.get("criado_em_x", row.get("criado_em"))
                    data_formatada = (
                        pd.to_datetime(data_raw, errors="coerce").strftime("%d/%m/%Y")
                        if pd.notna(data_raw)
                        else "N/D"
                    )

                    tag_ia = row.get("sentimento_ia", "Sem IA")
                    resumo_ia = row.get("resumo_ia", "")

                    try:
                        res_sdr = (
                            supabase.table("usuarios")
                            .select("foto_url")
                            .eq("nome", nome_colaborador)
                            .execute()
                        )
                        foto_sdr = None
                        if (
                            hasattr(res_sdr, "data")
                            and isinstance(res_sdr.data, list)
                            and len(res_sdr.data) > 0
                        ):
                            if isinstance(res_sdr.data[0], dict):
                                foto_sdr = res_sdr.data[0].get("foto_url")
                    except:
                        foto_sdr = None

                    with cols[i % NUM_COLS]:
                        with st.container(border=True):

                            c_img, c_txt = st.columns([1, 2.5])
                            with c_img:
                                if foto_sdr:
                                    st.markdown(
                                        f'<img src="{foto_sdr}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover; border: 2px solid #1f77b4; margin-top: 5px;">',
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    st.markdown(
                                        '<div style="font-size: 40px; margin-top: -5px;">👤</div>',
                                        unsafe_allow_html=True,
                                    )
                            with c_txt:
                                st.markdown(f"**{nome_colaborador}**")
                                st.caption(f"📅 {data_formatada}")

                            st.divider()

                            st.markdown(
                                f"""
                                <div style='text-align: center; margin-bottom: 15px;'>
                                    <span style='font-size: 13px; color: #888;'>Nota Original</span><br>
                                    <span style='font-size: 32px; font-weight: bold; color: #ff4b4b;'>{nota_limpa}%</span>
                                </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            if st.button(
                                "⚖️ Abrir Ticket",
                                type="primary",
                                use_container_width=True,
                                key=f"btn_grid_{id_cont_limpo}",
                            ):
                                modal_julgamento(
                                    row,
                                    id_cont_limpo,
                                    nota_limpa,
                                    auditor_original,
                                    nome_colaborador,
                                    data_formatada,
                                    tag_ia,
                                    resumo_ia,
                                    mapa_pesos,
                                )

            with aba_h:
                julgadas = df_completo[df_completo["status"] != "Pendente"].copy()
                if not julgadas.empty:
                    col_exib = (
                        "sdr_y"
                        if "sdr_y" in julgadas.columns
                        else (
                            "sdr_x"
                            if "sdr_x" in julgadas.columns
                            else ("sdr" if "sdr" in julgadas.columns else "sdr_nome")
                        )
                    )

                    col_data = (
                        "criado_em_x"
                        if "criado_em_x" in julgadas.columns
                        else "criado_em"
                    )

                    if col_data in julgadas.columns:
                        julgadas[col_data] = pd.to_datetime(
                            julgadas[col_data], errors="coerce"
                        )
                        julgadas = julgadas.sort_values(by=col_data, ascending=False)
                        julgadas["Data_Vis"] = (
                            julgadas[col_data].dt.strftime("%d/%m/%Y").fillna("-")
                        )
                    else:
                        julgadas["Data_Vis"] = "-"

                    st.dataframe(
                        julgadas[
                            ["Data_Vis", col_exib, "status", "nota", "resposta_admin"]
                        ],
                        column_config={
                            "Data_Vis": "Data Julg.",
                            col_exib: "Colaborador",
                            "status": "Status",
                            "nota": "Nota Final",
                            "resposta_admin": "Veredito (Feedback)",
                        },
                        use_container_width=True,
                        hide_index=True,
                    )