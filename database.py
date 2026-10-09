import time
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st
from supabase.client import Client, create_client


# ==========================================================
# 🔌 INICIALIZAÇÃO E TIMEZONE
# ==========================================================
def obter_hora_brasil():
    fuso = pytz.timezone("America/Sao_Paulo")
    return datetime.now(fuso).isoformat()


@st.cache_resource
def init_connection() -> Client | None:
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        if not url or not key:
            return None
        return create_client(str(url), str(key))
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None


supabase = init_connection()


# ==========================================================
# 📥 LEITURA COM CACHE INTELIGENTE E RETRY DE REDE
# ==========================================================
# Aumentamos o TTL para 300s (5min) para performance máxima em painéis BI.
@st.cache_data(ttl=300, show_spinner=False)
def get_all_records_db(tabela: str) -> pd.DataFrame:
    if not supabase:
        return pd.DataFrame()

    # Retry de 3 tentativas para blindar contra falhas curtas de internet (Errno 11)
    for tentativa in range(3):
        try:
            res = (
                supabase.table(tabela)
                .select("*")
                .order("criado_em", desc=True)
                .execute()
            )  # type: ignore
            if hasattr(res, "data") and res.data:
                return pd.DataFrame(res.data)
            return pd.DataFrame()
        except Exception as e:
            if tentativa == 2:  # Só avisa se falhar as 3 vezes
                print(f"Erro persistente ao buscar {tabela}: {e}")
                return pd.DataFrame()
            time.sleep(0.5)

    return pd.DataFrame()


# ==========================================================
# 🕵️ LOG DE AUDITORIA (CÂMERAS DE SEGURANÇA BLINDADAS)
# ==========================================================
def registrar_auditoria(
    acao: str,
    detalhes: str = "",
    colaborador_afetado: str = "N/A",
    nome_ator_explicito: str | None = None,
):
    if not supabase:
        return
    try:
        ator_responsavel = (
            str(nome_ator_explicito)
            if nome_ator_explicito
            else str(st.session_state.get("user_nome", "Sistema"))
        )
        payload = {
            "acao": str(acao),
            "admin_responsavel": ator_responsavel,
            "colaborador_afetado": str(colaborador_afetado),
            "detalhes": str(detalhes),
            "data_evento": obter_hora_brasil(),
        }
        supabase.table("auditoria").insert(payload).execute()  # type: ignore
    except Exception as e:
        print(f"🚨 Falha Crítica ao gravar Log de Auditoria: {e}")


# ==========================================================
# 📝 SALVAR MONITORIA
# ==========================================================
def salvar_monitoria_auditada(dados: dict):
    if not supabase:
        return False, "Sem banco de dados."
    try:
        dados["visualizada"] = False
        dados["criado_em"] = obter_hora_brasil()

        supabase.table("monitorias").insert(dados).execute()  # type: ignore
        get_all_records_db.clear()

        registrar_auditoria(
            acao="MONITORIA REALIZADA",
            detalhes=f"Nota: {dados.get('nota')}%",
            colaborador_afetado=str(dados.get("sdr", "N/A")),
        )
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)


# ==========================================================
# 🔔 SISTEMA DE NOTIFICAÇÕES (UNIFICADO E COM CACHE/RETRY)
# ==========================================================
@st.cache_data(ttl=15, show_spinner=False)  # Segura as requisições do sino por 15s
def buscar_contagem_notificacoes(nome_usuario: str, nivel: str) -> int:
    if not supabase or not nome_usuario or nome_usuario == "Usuário":
        return 0

    # Tenta buscar até 3 vezes (Resolve o Errno 11 instantaneamente)
    for _ in range(3):
        try:
            res_notif = (
                supabase.table("notificacoes")
                .select("id", count="exact")
                .eq("usuario", nome_usuario)
                .eq("lida", False)
                .execute()
            )  # type: ignore
            return (
                int(res_notif.count)
                if hasattr(res_notif, "count") and res_notif.count
                else 0
            )
        except Exception:
            time.sleep(0.5)

    return 0


def limpar_todas_notificacoes(nome_usuario: str):
    if not supabase:
        return
    try:
        # Limpa as antigas (para retrocompatibilidade)
        supabase.table("monitorias").update({"visualizada": True}).eq(
            "sdr", nome_usuario
        ).execute()  # type: ignore
        supabase.table("contestacoes").update({"visualizada": True}).eq(
            "sdr_nome", nome_usuario
        ).neq("status", "Pendente").execute()  # type: ignore

        # Limpa a tabela principal nova
        supabase.table("notificacoes").update({"lida": True}).eq(
            "usuario", nome_usuario
        ).execute()  # type: ignore

        get_all_records_db.clear()
        buscar_contagem_notificacoes.clear()
    except:
        pass


def limpar_notificacao_individual(id_notificacao, nome_usuario):
    if not supabase:
        return
    try:
        supabase.table("notificacoes").update({"lida": True}).eq(
            "id", id_notificacao
        ).execute()  # type: ignore
        buscar_contagem_notificacoes.clear()
    except Exception as e:
        print(f"Erro ao limpar notificação: {e}")


# ==========================================================
# 🗑️ ANULAR MONITORIA & APAGAR FOTOS
# ==========================================================
def anular_monitoria_auditada(id_monitoria, motivo, nome_responsavel):
    if not supabase:
        return False, "Sem banco de dados."
    try:
        res_mon = (
            supabase.table("monitorias").select("*").eq("id", id_monitoria).execute()
        )  # type: ignore
        if not hasattr(res_mon, "data") or not res_mon.data:
            return False, "Não encontrada."

        dados_mon = res_mon.data[0]

        if not isinstance(dados_mon, dict):
            return False, "Erro de formato nos dados da monitoria."

        sdr_afetado = str(dados_mon.get("sdr", "N/A"))
        detalhes = dados_mon.get("detalhes", {})

        arquivos_para_apagar = []
        if isinstance(detalhes, dict):
            for pergunta, info in detalhes.items():
                if isinstance(info, dict) and info.get("url_arquivo"):
                    url_completa = info["url_arquivo"]
                    nome_arquivo_storage = str(url_completa).split("/")[-1]
                    if nome_arquivo_storage:
                        arquivos_para_apagar.append(nome_arquivo_storage)

        if arquivos_para_apagar:
            try:
                supabase.storage.from_("evidencias").remove(arquivos_para_apagar)  # type: ignore
            except Exception as e:
                print(f"Aviso: Falha ao apagar fotos do Storage: {e}")

        supabase.table("contestacoes").delete().eq(
            "monitoria_id", id_monitoria
        ).execute()  # type: ignore
        supabase.table("monitorias").delete().eq("id", id_monitoria).execute()  # type: ignore

        detalhes_log = f"ID: {id_monitoria} | Motivo: {motivo} | Fotos apagadas: {len(arquivos_para_apagar)}"
        registrar_auditoria(
            "ANULAR_MONITORIA", detalhes_log, sdr_afetado, str(nome_responsavel)
        )

        get_all_records_db.clear()
        return True, "Anulada e arquivos apagados."
    except Exception as e:
        return False, str(e)


# ==========================================================
# 🗑️ REMOVER FOTO ESPECÍFICA (SEM ANULAR A MONITORIA)
# ==========================================================
def remover_evidencia_monitoria(
    id_monitoria, nome_criterio, url_arquivo, nome_responsavel
):
    if not supabase:
        return False, "Sem banco de dados."
    try:
        res_mon = (
            supabase.table("monitorias").select("*").eq("id", id_monitoria).execute()
        )  # type: ignore
        if not hasattr(res_mon, "data") or not res_mon.data:
            return False, "Monitoria não encontrada."

        dados_mon = res_mon.data[0]

        if not isinstance(dados_mon, dict):
            return False, "Erro de formato nos dados da monitoria."

        sdr_afetado = str(dados_mon.get("sdr", "N/A"))
        detalhes = dados_mon.get("detalhes", {})

        if url_arquivo:
            nome_arquivo_storage = str(url_arquivo).split("/")[-1]
            if nome_arquivo_storage:
                try:
                    supabase.storage.from_("evidencias").remove([nome_arquivo_storage])  # type: ignore
                except Exception as e:
                    print(f"Aviso: Falha ao apagar do Storage: {e}")

        if isinstance(detalhes, dict) and nome_criterio in detalhes:
            criterio_alvo = detalhes[nome_criterio]
            if isinstance(criterio_alvo, dict):
                criterio_alvo["url_arquivo"] = None
                criterio_alvo["evidencia_anexada"] = False
                supabase.table("monitorias").update({"detalhes": detalhes}).eq(
                    "id", id_monitoria
                ).execute()  # type: ignore

        detalhes_log = f"ID: {id_monitoria} | Critério: '{nome_criterio}' | Foto apagada manualmente."
        registrar_auditoria(
            "REMOVER_EVIDENCIA", detalhes_log, sdr_afetado, str(nome_responsavel)
        )

        get_all_records_db.clear()
        return True, "Foto apagada com sucesso!"
    except Exception as e:
        return False, str(e)
