import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import os
import base64

from auth import render_login
from dashboard import render_dashboard
from monitoria import render_nova_monitoria
from contestacao import render_contestacao
from cadastro import render_cadastro
from meus_resultados import render_meus_resultados
from usuarios_gestao import render_usuario_gestao
from meu_perfil import render_meu_perfil
from auditoria import render_auditoria
from relatorios import render_relatorios
from gestao_criterios import render_gestao_criterios
from matriz_decisao import render_pdi
from historico_monitorias import render_historico_monitorias

# --- COMENTADO: Módulo de Liderança pausado por decisão em reunião ---
# from avaliacao_lideranca import render_avaliacao_lideranca, render_dashboard_lideranca, obter_ciclo_atual
# ---------------------------------------------------------------------

from style import apply_custom_styles
from database import (
    get_all_records_db,
    supabase,
    buscar_contagem_notificacoes,
    limpar_todas_notificacoes,
    limpar_notificacao_individual,
    anular_monitoria_auditada,
    registrar_auditoria,
    remover_evidencia_monitoria,
)


# ==========================================================
# 🔔 FUNÇÃO DE ÁUDIO INVISÍVEL (SINAL SONORO ESTILO IPHONE)
# ==========================================================
def tocar_som_notificacao():
    """Lê o arquivo local de áudio e injeta um player invisível na tela"""

    # Procura o som do iPhone na sua pasta assets
    caminho_som = "assets/iphone.mp3"

    try:
        if os.path.exists(caminho_som):
            # Transforma o MP3 local num código base64 para tocar direto no navegador
            with open(caminho_som, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                som_src = f"data:audio/mp3;base64,{b64}"
        else:
            # Som de backup (estilo smartphone) caso o arquivo iphone.mp3 não seja encontrado
            som_src = (
                "https://assets.mixkit.co/active_storage/sfx/2866/2866-preview.mp3"
            )

        html_som = f"""
            <audio autoplay style="display:none;">
                <source src="{som_src}" type="audio/mp3">
            </audio>
        """
        st.markdown(html_som, unsafe_allow_html=True)

    except Exception as e:
        print(f"Erro ao tentar tocar o som: {e}")


# ==========================================================
# MODAL DE ANULAR AUDITORIA
# ==========================================================
@st.dialog("🗑️ Confirmar Anulação")
def modal_anular(id_mon, sdr_nome):
    st.warning(f"Deseja excluir permanentemente a monitoria de **{sdr_nome}**?")
    st.markdown(
        "<small style='color: #ff4b4b;'>⚠️ Esta ação removerá a nota do cálculo de média e apagará as fotos anexadas.</small>",
        unsafe_allow_html=True,
    )
    motivo = st.text_input("Motivo obrigatório para auditoria:")

    col_a, col_b = st.columns(2)
    if col_a.button("Confirmar Exclusão", type="primary", use_container_width=True):
        if not motivo or len(motivo) < 5:
            st.error("Escreva um motivo válido.")
        else:
            quem_esta_logado = str(
                st.session_state.get("user_nome", "Admin Desconhecido")
            )
            sucesso, msg = anular_monitoria_auditada(id_mon, motivo, quem_esta_logado)
            if sucesso:
                st.success("Registro removido e arquivos apagados da nuvem!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error(f"Erro: {msg}")

    if col_b.button("Cancelar", use_container_width=True):
        st.rerun()

# ==========================================================
# HISTÓRICO GERAL ATUALIZADO (COM COLUNA DE FEEDBACK)
# ==========================================================
def render_historico_geral(nivel, nome_completo):
    dept_selecionado = str(st.session_state.get("departamento_selecionado", "Todos"))
    st.title(f"📚 Histórico Consolidado - {dept_selecionado}")

    if st.button("🔄 Atualizar Dados"):
        get_all_records_db.clear()
        st.rerun()

    df_monitorias = get_all_records_db("monitorias")
    df_contestacoes = get_all_records_db("contestacoes")

    if df_monitorias is None or df_monitorias.empty:
        st.info("Nenhuma monitoria encontrada.")
        return

    df_monitorias["id"] = df_monitorias["id"].astype(str).str.strip()

    df_monitorias["criado_em"] = pd.to_datetime(
        df_monitorias["criado_em"], errors="coerce"
    )
    df_monitorias = df_monitorias.dropna(subset=["criado_em"]).sort_values(
        by="criado_em", ascending=False
    )

    if df_contestacoes is not None and not df_contestacoes.empty:
        df_contestacoes["id"] = df_contestacoes["id"].astype(str).str.strip()
        df_contestacoes["monitoria_id"] = (
            df_contestacoes["monitoria_id"].astype(str).str.strip()
        )
        df_cont_resumo = df_contestacoes[
            ["monitoria_id", "status", "resposta_admin"]
        ].rename(columns={"status": "Situação"})
        df_exibicao = pd.merge(
            df_monitorias,
            df_cont_resumo,
            left_on="id",
            right_on="monitoria_id",
            how="left",
        )
        df_exibicao["Situação"] = df_exibicao["Situação"].fillna("Nenhuma")
    else:
        df_exibicao = df_monitorias.copy()
        df_exibicao["Situação"] = "Nenhuma"

    # 👇 NOVA MÁGICA: CRIANDO A COLUNA "FB REALIZADO"
    def verificar_fb(valor):
        val_str = str(valor).strip().lower()
        # Se for vazio, nulo, NaN ou None, retorna Não
        if val_str in ["", "nan", "none", "null"] or pd.isna(valor):
            return "❌ Não"
        return "✅ Sim"
        
    if "resposta_gestor" in df_exibicao.columns:
        df_exibicao["Fb Realizado"] = df_exibicao["resposta_gestor"].apply(verificar_fb)
    else:
        df_exibicao["Fb Realizado"] = "❌ Não"

    if dept_selecionado != "Todos" and "departamento" in df_exibicao.columns:
        df_exibicao = df_exibicao[
            df_exibicao["departamento"].astype(str).str.strip().str.upper()
            == dept_selecionado.strip().upper()
        ].copy()

    if nivel != "ADMIN":
        df_exibicao = df_exibicao[
            (df_exibicao["sdr"].astype(str) != "admin@grupoacelerador.com.br")
            & (
                df_exibicao["monitor_responsavel"].astype(str)
                != "admin@grupoacelerador.com.br"
            )
        ].copy()

    if nivel not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
        df_exibicao = df_exibicao[
            df_exibicao["sdr"].astype(str).str.strip().str.upper()
            == nome_completo.strip().upper()
        ].copy()

    if df_exibicao.empty:
        st.info("Nenhum dado encontrado para o seu perfil/departamento.")
        return

    # --- SEÇÃO DE FILTROS AVANÇADOS PARA LIDERANÇA ---
    if nivel in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
        with st.expander("🔎 Filtros Avançados", expanded=True):
            # Transformei em 5 colunas para o novo filtro de Feedback
            col1, col2, col3, col4, col5 = st.columns(5)

            lista_sdrs = ["Todos"] + sorted(
                df_exibicao["sdr"].dropna().unique().tolist()
            )
            filtro_sdr = col1.selectbox("Colaborador:", lista_sdrs)

            lista_avaliadores = ["Todos"] + sorted(
                df_exibicao["monitor_responsavel"].dropna().unique().tolist()
            )
            filtro_avaliador = col2.selectbox("Avaliador:", lista_avaliadores)

            lista_situacoes = ["Todas"] + sorted(
                df_exibicao["Situação"].astype(str).unique().tolist()
            )
            filtro_situacao = col3.selectbox("Contestação:", lista_situacoes)
            
            # 👇 NOVO FILTRO DE FEEDBACK
            lista_fb = ["Todos", "✅ Sim", "❌ Não"]
            filtro_fb = col4.selectbox("FB Realizado?", lista_fb)

            df_exibicao["MesAno"] = df_exibicao["criado_em"].dt.strftime("%m/%Y")
            lista_meses = ["Todos"] + df_exibicao["MesAno"].dropna().unique().tolist()
            filtro_mes = col5.selectbox("Mês/Ano:", lista_meses)

            if filtro_sdr != "Todos":
                df_exibicao = df_exibicao[df_exibicao["sdr"] == filtro_sdr]
            if filtro_avaliador != "Todos":
                df_exibicao = df_exibicao[
                    df_exibicao["monitor_responsavel"] == filtro_avaliador
                ]
            if filtro_situacao != "Todas":
                df_exibicao = df_exibicao[df_exibicao["Situação"] == filtro_situacao]
            if filtro_fb != "Todos":
                df_exibicao = df_exibicao[df_exibicao["Fb Realizado"] == filtro_fb]
            if filtro_mes != "Todos":
                df_exibicao = df_exibicao[df_exibicao["MesAno"] == filtro_mes]

    df_exibicao["Data"] = (
        df_exibicao["criado_em"].dt.strftime("%d/%m/%Y %H:%M").fillna("Data N/D")
    )

    if df_exibicao.empty:
        st.warning("Nenhum registro corresponde aos filtros selecionados.")
        return

    # 👇 Atualizei as colunas de exibição da tabela para mostrar o "Fb Realizado"
    st.dataframe(
        df_exibicao[["Data", "sdr", "nota", "monitor_responsavel", "Situação", "Fb Realizado"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "nota": st.column_config.ProgressColumn(
                "Nota", format="%d%%", min_value=0, max_value=100
            ),
            "Fb Realizado": st.column_config.TextColumn(
                "FB Realizado?"
            )
        },
    )

    st.divider()
    st.subheader("🔍 Ver Detalhes da Monitoria")

    opcoes_hist = {
        f"📅 {row['Data']} | Avaliado: {row['sdr']} | Nota: {row['nota']}%": row["id"]
        for _, row in df_exibicao.iterrows()
    }
    escolha = st.selectbox("Escolha a Avaliação:", [""] + list(opcoes_hist.keys()))

    if escolha:
        id_sel = opcoes_hist[escolha]
        linha = df_exibicao[df_exibicao["id"] == id_sel].iloc[0]
        auditor_nome = linha["monitor_responsavel"]

        try:
            foto_auditor = None
            if supabase is not None:
                res_aud = supabase.table("usuarios").select("foto_url").eq("nome", auditor_nome).execute()  # type: ignore
                if res_aud.data and isinstance(res_aud.data[0], dict):
                    foto_auditor = res_aud.data[0].get("foto_url")
        except:
            foto_auditor = None

        with st.container(border=True):
            c_f, c_t = st.columns([1, 4])
            with c_f:
                if foto_auditor:
                    st.markdown(
                        f'<img src="{foto_auditor}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid #ff4b4b;">',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="font-size: 60px;">🕵️</div>', unsafe_allow_html=True
                    )
            with c_t:
                st.markdown(f"#### Avaliador: {auditor_nome}")
                st.markdown(
                    f"**Avaliado:** {linha['sdr']} | **Nota:** `{linha['nota']}%`"
                )

            if linha.get("observacoes"):
                st.info(f"💬 **Feedback do Auditor:** {linha['observacoes']}")
                
            if linha.get("resposta_gestor") and str(linha.get("resposta_gestor")).lower() != 'nan':
                st.success(f"🎯 **Plano de Ação do Gestor (1:1):** {linha['resposta_gestor']}")

            c_l1, c_l2 = st.columns(2)
            if linha.get("link_selene"):
                c_l1.markdown(f"🔗 [Gravação Selene]({linha['link_selene']})")
            if linha.get("link_nectar"):
                c_l2.markdown(f"🗂️ [Card CRM Nectar]({linha['link_nectar']})")

        st.markdown("### 📋 Detalhamento")
        detalhes = linha.get("detalhes")
        if detalhes and isinstance(detalhes, dict):
            for pergunta, info in detalhes.items():
                if isinstance(info, dict):
                    nota_c = info.get("nota", "NSA")
                    coment = info.get("comentario", "Sem comentário.")
                    tem_anexo = info.get("evidencia_anexada", False)
                    url_img = info.get("url_arquivo")
                    nome_arq = info.get("arquivo", "Anexo")

                    if nota_c == "C":
                        if tem_anexo or (coment and coment != "Sem comentário."):
                            with st.expander(
                                f"✅ {pergunta} (Conforme)", expanded=False
                            ):
                                if coment and coment != "Sem comentário.":
                                    st.write(f"**Comentário:** {coment}")
                                if tem_anexo and url_img:
                                    st.image(
                                        url_img,
                                        caption=f"Evidência Positiva: {nome_arq}",
                                        use_container_width=True,
                                    )
                                    col_link, col_btn = st.columns([3, 1])
                                    col_link.markdown(
                                        f"🔗 [Abrir Imagem Original]({url_img})"
                                    )
                                    if nivel in ["ADMIN", "AUDITOR"]:
                                        if col_btn.button(
                                            "🗑️ Apagar Foto",
                                            key=f"del_img_{id_sel}_{pergunta}",
                                        ):
                                            sucesso, msg = remover_evidencia_monitoria(
                                                id_sel, pergunta, url_img, nome_completo
                                            )
                                            if sucesso:
                                                registrar_auditoria(
                                                    "EXCLUSÃO EVIDÊNCIA",
                                                    f"Apagou foto da monitoria de {linha['sdr']}",
                                                    str(linha["sdr"]),
                                                    nome_completo,
                                                )
                                                st.success("✅ " + msg)
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("❌ " + msg)
                    elif nota_c in ["NC", "NGC", "NC Grave"]:
                        with st.expander(
                            f"❌ {pergunta} (Penalidade: {nota_c})", expanded=True
                        ):
                            st.write(f"**Motivo:** {coment}")
                            if tem_anexo:
                                if url_img:
                                    st.image(
                                        url_img,
                                        caption=f"Evidência: {nome_arq}",
                                        use_container_width=True,
                                    )
                                    col_link, col_btn = st.columns([3, 1])
                                    col_link.markdown(
                                        f"🔗 [Abrir Imagem Original]({url_img})"
                                    )
                                    if nivel in ["ADMIN", "AUDITOR"]:
                                        if col_btn.button(
                                            "🗑️ Apagar Foto",
                                            key=f"del_img_{id_sel}_{pergunta}",
                                        ):
                                            sucesso, msg = remover_evidencia_monitoria(
                                                id_sel, pergunta, url_img, nome_completo
                                            )
                                            if sucesso:
                                                registrar_auditoria(
                                                    "EXCLUSÃO EVIDÊNCIA",
                                                    f"Apagou foto da monitoria de {linha['sdr']}",
                                                    str(linha["sdr"]),
                                                    nome_completo,
                                                )
                                                st.success("✅ " + msg)
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("❌ " + msg)
                    else:
                        st.markdown(f"➖ **{pergunta}** (NSA)")

        if nivel == "ADMIN":
            st.divider()
            if st.button(
                "🗑️ Excluir esta Auditoria", type="primary", use_container_width=True
            ):
                modal_anular(id_sel, linha["sdr"])

# ==========================================================
# 🚀 MÁGICA: COMPONENTE DE SINO EM TEMPO REAL
# ==========================================================
@st.fragment(run_every="15s")
def render_sininho_live(nome_completo, nivel):
    # 1. Força a limpeza do cache para pegar o dado em tempo real do banco
    buscar_contagem_notificacoes.clear()
    res_n = buscar_contagem_notificacoes(nome_completo, nivel)
    qtd = int(res_n if res_n else 0)

    # 2. Compara se chegou notificação nova para soltar aviso visual e sonoro
    if "ultima_qtd_notif" not in st.session_state:
        st.session_state.ultima_qtd_notif = qtd
    elif qtd > st.session_state.ultima_qtd_notif:
        st.toast("🔔 Você recebeu uma nova mensagem ou avaliação!", icon="✨")

        # 🎵 DISPARA O SOM DO SININHO AQUI!
        tocar_som_notificacao()

        st.session_state.ultima_qtd_notif = qtd
    elif qtd < st.session_state.ultima_qtd_notif:
        st.session_state.ultima_qtd_notif = qtd

    # 3. Desenha o botão Popover (Gaveta)
    label_sino = f"🔔 {qtd}" if qtd > 0 else "🔕"

    with st.popover(label_sino):
        st.markdown("#### Suas Mensagens")
        notifs = []
        sucesso_busca = False

        # Leve tolerância de rede
        for _ in range(3):
            try:
                if supabase is not None:
                    res = supabase.table("notificacoes").select("*").eq("usuario", nome_completo).eq("lida", False).order("id", desc=True).execute()  # type: ignore
                    notifs = res.data if res.data else []
                    sucesso_busca = True
                    break
            except Exception:
                time.sleep(0.5)

        if sucesso_busca:
            if notifs:
                for notif in notifs:
                    if isinstance(notif, dict):
                        msg_texto = str(notif.get("mensagem", ""))
                        id_notif = notif.get("id")

                        col_msg, col_x = st.columns([5, 1])

                        with col_msg:
                            if (
                                "Medalha" in msg_texto
                                or "PARABÉNS" in msg_texto
                                or "Sniper" in msg_texto
                                or "Muralha" in msg_texto
                            ):
                                st.success(msg_texto)
                            else:
                                st.info(msg_texto)

                        with col_x:
                            if st.button(
                                "✖️",
                                key=f"del_notif_{id_notif}",
                                help="Dispensar aviso",
                            ):
                                limpar_notificacao_individual(id_notif, nome_completo)
                                st.session_state.ultima_qtd_notif = max(
                                    0, st.session_state.ultima_qtd_notif - 1
                                )
                                st.rerun()

                st.divider()
                if st.button(
                    "✅ Limpar Todas as Lidas", use_container_width=True, type="primary"
                ):
                    limpar_todas_notificacoes(nome_completo)
                    st.session_state.ultima_qtd_notif = 0
                    st.rerun()
            else:
                st.caption("Você está em dia! Nenhuma novidade por aqui. 😎")
        else:
            st.caption("A rede oscilou. Tente abrir novamente em instantes.")


# ==========================================================
# FUNÇÃO PRINCIPAL E SIDEBAR PREMIUM
# ==========================================================
def main():
    icon_path = "assets/icon.png" if os.path.exists("assets/logo.png") else "🚀"
    st.set_page_config(layout="wide", page_title="Acelera Quality", page_icon=icon_path)

    # CSS MÁGICO DOS BOTÕES E POPOVER (COM ESTILIZAÇÃO DO SINO)
    st.markdown(
        """
    <style>
    section[data-testid='stSidebar'] { display: block !important; visibility: visible !important; }
    
    /* ESTILO PREMIUM PARA TODOS OS BOTÕES DA SIDEBAR */
    [data-testid="stSidebar"] div.stButton > button {
        width: 100%;
        border: none;
        background-color: transparent;
        color: inherit;
        text-align: left;
        justify-content: flex-start;
        padding: 8px 15px;
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
        box-shadow: none;
        margin-bottom: 2px;
    }
    
    /* Efeito Hover nos botões do menu */
    [data-testid="stSidebar"] div.stButton > button:hover {
        background-color: rgba(255, 122, 0, 0.1);
        color: #FF7A00;
        transform: translateX(4px);
    }

    /* Botão do Menu ATIVO */
    [data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background-color: rgba(255, 122, 0, 0.15); 
        color: #FF7A00;
        font-weight: bold;
        border-left: 4px solid #FF7A00;
        border-radius: 4px 8px 8px 4px;
    }

    /* =======================================================
       ESTILIZAÇÃO PREMIUM DO SINO (Removendo Setinha e Wrap)
       ======================================================= */
    
    /* Remove a setinha (chevron) padrão do Popover */
    [data-testid="stSidebar"] div[data-testid="stPopover"] > button svg {
        display: none !important;
    }
    
    /* Força o conteúdo do sino a ficar em uma linha só e centralizado */
    [data-testid="stSidebar"] div[data-testid="stPopover"] > button div,
    [data-testid="stSidebar"] div[data-testid="stPopover"] > button span {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        gap: 4px !important;
    }
    
    /* Pílula flutuante Laranja Tech para o Sino */
    [data-testid="stSidebar"] div[data-testid="stPopover"] > button {
        width: 100% !important;
        padding: 6px 12px !important;
        background-color: rgba(255, 122, 0, 0.15) !important;
        border: 1px solid rgba(255, 122, 0, 0.4) !important;
        border-radius: 20px !important;
        box-shadow: none !important;
        font-size: 14px !important;
        color: #FF7A00 !important;
        font-weight: 800 !important;
        height: auto !important;
        min-height: 0 !important;
        line-height: 1 !important;
        margin-top: 5px !important;
    }
    
    /* Efeito Hover do Sino */
    [data-testid="stSidebar"] div[data-testid="stPopover"] > button:hover {
        background-color: rgba(255, 122, 0, 0.3) !important;
        border-color: #FF7A00 !important;
        transform: scale(1.05);
        transition: transform 0.2s ease;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "departamento_selecionado" not in st.session_state:
        st.session_state.departamento_selecionado = "Todos"
    if "current_page" not in st.session_state:
        st.session_state.current_page = "DASHBOARD"

    if not st.session_state.authenticated:
        render_login()
        st.stop()

    apply_custom_styles()

    nivel = str(st.session_state.nivel)
    nome_completo = str(st.session_state.user_nome)
    meu_dept = str(st.session_state.get("departamento", nivel))

    # ==========================================
    # CONSTRUÇÃO DO MENU LATERAL (SIDEBAR)
    # ==========================================
    with st.sidebar:
        # 1. LOGO
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", use_container_width=True)
        else:
            st.markdown(
                "<h2 style='text-align:center; color:#FF7A00; margin-top:0;'>ACELERA QUALITY</h2>",
                unsafe_allow_html=True,
            )
        st.write("---")

        # 2. CARTÃO DE PERFIL COM O SININHO DISCRETO
        with st.container(border=True):
            col_img, col_dados, col_bell = st.columns([1, 2.5, 1.3])
            foto_p = st.session_state.get("foto_url")

            with col_img:
                if foto_p:
                    st.markdown(
                        f"<img src='{foto_p}' style='width:50px;height:50px;border-radius:50%;object-fit:cover;border:2px solid #FF7A00;'>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='font-size:35px; margin-top:-5px; color: #FF7A00;'>👤</div>",
                        unsafe_allow_html=True,
                    )

            with col_dados:
                nome_curto = (
                    " ".join(nome_completo.split()[:2])
                    if len(nome_completo.split()) > 1
                    else nome_completo
                )
                st.markdown(
                    f"<div style='font-size: 13px; font-weight: bold;'>{nome_curto}</div>",
                    unsafe_allow_html=True,
                )

                if nivel == "ADMIN":
                    rotulo_perfil = "Administrador"
                elif nivel == "GERENCIA":
                    rotulo_perfil = "Gerência"
                else:
                    rotulo_perfil = meu_dept

                st.markdown(
                    f"<span style='background-color: #FF7A0022; color: #FF7A00; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: bold; border: 1px solid #FF7A0044; text-transform: uppercase;'>{rotulo_perfil}</span>",
                    unsafe_allow_html=True,
                )

            with col_bell:
                render_sininho_live(nome_completo, nivel)

        # 3. FILTRO GLOBAL (SÓ PARA LIDERANÇA)
        if nivel in ["ADMIN", "AUDITOR", "GERENCIA", "GESTAO"]:
            st.write("##")
            with st.container(border=True):
                st.markdown("🌐 **Visão Global**")
                if nivel == "GESTAO":
                    st.session_state.departamento_selecionado = meu_dept
                    st.selectbox(
                        "Filtrar setor:",
                        [meu_dept],
                        index=0,
                        disabled=True,
                        label_visibility="collapsed",
                    )
                else:
                    opcoes_d = [
                        "Todos",
                        "SDR",
                        "Especialista",
                        "Venda de Ingresso",
                        "Auditor",
                    ]
                    idx_atual = (
                        opcoes_d.index(st.session_state.departamento_selecionado)
                        if st.session_state.departamento_selecionado in opcoes_d
                        else 0
                    )
                    st.session_state.departamento_selecionado = st.selectbox(
                        "Filtrar setor:",
                        opcoes_d,
                        index=idx_atual,
                        label_visibility="collapsed",
                    )
        else:
            st.session_state.departamento_selecionado = meu_dept

        # ==========================================
        # 4. MENU DE NAVEGAÇÃO DIVIDIDO EM SEÇÕES
        # ==========================================
        st.write("##")

        # Mapeamento do Menu Agrupado
        menu_groups = {
            "📊 VISÃO GERAL": {},
            "⚡ OPERAÇÃO": {},
            "⚙️ ADMINISTRAÇÃO": {},
            "👤 MINHA CONTA": {},
        }

        # Regras de Visibilidade baseadas no Nível
        menu_groups["📊 VISÃO GERAL"]["📊 Dashboard"] = "DASHBOARD"

        if nivel not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            # VISÃO DO SDR / ESPECIALISTA
            menu_groups["📊 VISÃO GERAL"]["📈 Meus Resultados"] = "MEUS_RESULTADOS"
            menu_groups["📊 VISÃO GERAL"]["📚 Histórico"] = "HISTORICO"

            menu_groups["⚡ OPERAÇÃO"]["⚖️ Contestar Nota"] = "CONTESTACAO"
            menu_groups["⚡ OPERAÇÃO"]["🎯 Meu PDI"] = "PDI"
        else:
            # VISÃO DA LIDERANÇA E ADMIN
            menu_groups["📊 VISÃO GERAL"]["📚 Histórico Geral"] = "HISTORICO"

            if nivel in ["ADMIN", "GERENCIA", "AUDITOR", "GESTAO"]:
                menu_groups["📊 VISÃO GERAL"]["📋 Relatórios"] = "RELATORIOS"

            if nivel in ["ADMIN", "GERENCIA", "AUDITOR"]:
                menu_groups["⚡ OPERAÇÃO"]["📝 Nova Monitoria"] = "MONITORIA"
                menu_groups["⚡ OPERAÇÃO"]["⚖️ Contestações"] = "CONTESTACAO"

            # 👇 AQUI ADICIONAMOS O BOTÃO DA NOVA TELA DE FEEDBACK PARA A LIDERANÇA
            if nivel in ["ADMIN", "GERENCIA", "GESTAO", "AUDITOR"]:
                menu_groups["⚡ OPERAÇÃO"]["🎯 Feedbacks (1:1)"] = "FEEDBACKS"

            if nivel in ["ADMIN", "GERENCIA", "GESTAO"]:
                menu_groups["⚡ OPERAÇÃO"]["🎯 Matriz de Decisão"] = "PDI"

            if nivel in ["ADMIN", "GERENCIA"]:
                menu_groups["⚙️ ADMINISTRAÇÃO"][
                    "👥 Gestão de Equipe"
                ] = "GESTAO_USUARIOS"
                menu_groups["⚙️ ADMINISTRAÇÃO"]["👤 Cadastrar Usuário"] = "CADASTRO"

            if nivel in ["ADMIN", "AUDITOR"]:
                menu_groups["⚙️ ADMINISTRAÇÃO"][
                    "⚙️ Config. Critérios"
                ] = "CONFIG_CRITERIOS"

            if nivel == "ADMIN":
                menu_groups["⚙️ ADMINISTRAÇÃO"]["🕵️ Auditoria"] = "AUDITORIA"

        menu_groups["👤 MINHA CONTA"]["👤 Meu Perfil"] = "PERFIL"

        # Remove grupos vazios (Ex: SDR não verá 'Administração')
        menu_groups = {k: v for k, v in menu_groups.items() if v}

        # Função geradora de botões
        def render_menu_btn(label, target_page):
            btn_type = (
                "primary"
                if st.session_state.current_page == target_page
                else "secondary"
            )
            if st.button(label, use_container_width=True, type=btn_type):
                st.session_state.current_page = target_page
                st.rerun()

        # Renderização das Seções
        for section_name, items in menu_groups.items():
            st.caption(f"**{section_name}**")
            for label, target_page in items.items():
                render_menu_btn(label, target_page)
            st.write("")  # Espaçamento entre os blocos

        # ==========================================
        # 5. RODAPÉ E SAÍDA
        # ==========================================
        st.write("---")
        if st.session_state.get("logout_step"):
            st.warning("🔐 Deseja sair do sistema?")
            col_conf, col_canc = st.columns(2)
            if col_conf.button("Sair", type="primary", use_container_width=True):
                registrar_auditoria("LOGOUT", "Sessão encerrada.", "N/A", nome_completo)
                st.session_state.clear()
                st.rerun()
            if col_canc.button("Cancelar", use_container_width=True):
                st.session_state.logout_step = False
                st.rerun()
        else:
            if st.button("🚪 Sair do Sistema", use_container_width=True):
                st.session_state.logout_step = True

    # ==========================================
    # ROTEADOR DE PÁGINAS (Carrega a tela selecionada)
    # ==========================================
    page = st.session_state.current_page
    try:
        if page == "DASHBOARD":
            render_dashboard()
        elif page == "PERFIL":
            render_meu_perfil()
        elif page == "CONTESTACAO":
            render_contestacao()
        elif page == "MEUS_RESULTADOS":
            render_meus_resultados()
        elif page == "HISTORICO":
            render_historico_geral(nivel, nome_completo)
        # 👇 ROTA PARA A NOVA TELA DE FEEDBACK!
        elif page == "FEEDBACKS":
            render_historico_monitorias()
        elif page == "RELATORIOS":
            render_relatorios()
        elif page == "CADASTRO":
            render_cadastro()
        elif page == "MONITORIA":
            render_nova_monitoria()
        elif page == "GESTAO_USUARIOS":
            render_usuario_gestao()
        elif page == "CONFIG_CRITERIOS":
            render_gestao_criterios()
        elif page == "AUDITORIA":
            render_auditoria()
        elif page == "PDI":
            render_pdi()
    except Exception as e:
        st.error(f"Erro ao carregar a página: {e}")


if __name__ == "__main__":
    main()