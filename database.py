import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import pytz

# ==========================================================
# 🔌 INICIALIZAÇÃO E TIMEZONE
# ==========================================================
def obter_hora_brasil():
    fuso = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso).isoformat()

@st.cache_resource
def init_connection():
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        if not url or not key: return None
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

supabase = init_connection()

# ==========================================================
# 📥 LEITURA COM CACHE INTELIGENTE
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_all_records_db(tabela):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(tabela).select("*").order("criado_em", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# ==========================================================
# 🕵️ LOG DE AUDITORIA (CÂMERAS DE SEGURANÇA BLINDADAS)
# ==========================================================
def registrar_auditoria(acao, detalhes="", colaborador_afetado="N/A", nome_ator_explicito=None):
    try:
        ator_responsavel = nome_ator_explicito if nome_ator_explicito else st.session_state.get('user_nome', 'Sistema')
        payload = {
            "acao": acao,
            "admin_responsavel": ator_responsavel,
            "colaborador_afetado": colaborador_afetado,
            "detalhes": detalhes,
            "data_evento": obter_hora_brasil() 
        }
        supabase.table("auditoria").insert(payload).execute()
    except Exception as e:
        print(f"🚨 Falha Crítica ao gravar Log de Auditoria: {e}")

# ==========================================================
# 📝 SALVAR MONITORIA
# ==========================================================
def salvar_monitoria_auditada(dados):
    try:
        dados['visualizada'] = False 
        dados['criado_em'] = obter_hora_brasil()
        
        supabase.table("monitorias").insert(dados).execute()
        get_all_records_db.clear()
        
        registrar_auditoria(
            acao="MONITORIA REALIZADA", 
            detalhes=f"Nota: {dados.get('nota')}%", 
            colaborador_afetado=dados.get('sdr', 'N/A')
        )
        return True, "Sucesso"
    except Exception as e:
        return False, str(e)

# ==========================================================
# 🔔 SISTEMA DE NOTIFICAÇÕES (ATUALIZADO PARA PDI)
# ==========================================================
def buscar_contagem_notificacoes(nome_usuario, nivel):
    if not nome_usuario or nome_usuario == "Usuário": return 0
    try:
        # Busca notificações gerais não lidas (nova tabela)
        res_notif = supabase.table("notificacoes").select("id", count="exact").eq("usuario", nome_usuario).eq("lida", False).execute()
        qtd_notif_gerais = res_notif.count if res_notif.count else 0

        if nivel not in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]:
            # Conta monitorias e contestações antigas do SDR
            res_mon = supabase.table("monitorias").select("id", count="exact").eq("sdr", nome_usuario).eq("visualizada", False).execute()
            res_cont = supabase.table("contestacoes").select("id", count="exact").eq("sdr_nome", nome_usuario).neq("status", "Pendente").eq("visualizada", False).execute()
            
            qtd_mon = res_mon.count if res_mon.count else 0
            qtd_cont = res_cont.count if res_cont.count else 0
            
            return qtd_mon + qtd_cont + qtd_notif_gerais
        else:
            # Conta pendências da liderança + notificações próprias
            res = supabase.table("contestacoes").select("id", count="exact").eq("status", "Pendente").execute()
            qtd_pendentes = res.count if res.count else 0
            
            return qtd_pendentes + qtd_notif_gerais
    except: return 0

def limpar_todas_notificacoes(nome_usuario):
    try:
        # Limpa as antigas
        supabase.table("monitorias").update({"visualizada": True}).eq("sdr", nome_usuario).execute()
        supabase.table("contestacoes").update({"visualizada": True}).eq("sdr_nome", nome_usuario).neq("status", "Pendente").execute()
        # Limpa as novas da tabela de notificações (PDI, etc)
        supabase.table("notificacoes").update({"lida": True}).eq("usuario", nome_usuario).execute()
        
        get_all_records_db.clear()
    except: pass

# ==========================================================
# 🗑️ ANULAR MONITORIA & APAGAR FOTOS
# ==========================================================
def anular_monitoria_auditada(id_monitoria, motivo, nome_responsavel):
    try:
        res_mon = supabase.table("monitorias").select("*").eq("id", id_monitoria).execute()
        if not res_mon.data: return False, "Não encontrada."
        
        dados_mon = res_mon.data[0]
        sdr_afetado = dados_mon.get('sdr', 'N/A')
        detalhes = dados_mon.get('detalhes', {})

        arquivos_para_apagar = []
        if isinstance(detalhes, dict):
            for pergunta, info in detalhes.items():
                if isinstance(info, dict) and info.get('url_arquivo'):
                    url_completa = info['url_arquivo']
                    nome_arquivo_storage = url_completa.split('/')[-1]
                    if nome_arquivo_storage:
                        arquivos_para_apagar.append(nome_arquivo_storage)

        if arquivos_para_apagar:
            try:
                supabase.storage.from_("evidencias").remove(arquivos_para_apagar)
            except Exception as e:
                print(f"Aviso: Falha ao apagar fotos do Storage: {e}")

        supabase.table("contestacoes").delete().eq("monitoria_id", id_monitoria).execute()
        supabase.table("monitorias").delete().eq("id", id_monitoria).execute()
        
        detalhes_log = f"ID: {id_monitoria} | Motivo: {motivo} | Fotos apagadas: {len(arquivos_para_apagar)}"
        registrar_auditoria("ANULAR_MONITORIA", detalhes_log, sdr_afetado, nome_responsavel)
        
        get_all_records_db.clear()
        return True, "Anulada e arquivos apagados."
    except Exception as e: return False, str(e)

# ==========================================================
# 🗑️ REMOVER FOTO ESPECÍFICA (SEM ANULAR A MONITORIA)
# ==========================================================
def remover_evidencia_monitoria(id_monitoria, nome_criterio, url_arquivo, nome_responsavel):
    try:
        res_mon = supabase.table("monitorias").select("*").eq("id", id_monitoria).execute()
        if not res_mon.data: return False, "Monitoria não encontrada."
        
        dados_mon = res_mon.data[0]
        sdr_afetado = dados_mon.get('sdr', 'N/A')
        detalhes = dados_mon.get('detalhes', {})

        if url_arquivo:
            nome_arquivo_storage = url_arquivo.split('/')[-1]
            if nome_arquivo_storage:
                try:
                    supabase.storage.from_("evidencias").remove([nome_arquivo_storage])
                except Exception as e:
                    print(f"Aviso: Falha ao apagar do Storage: {e}")

        if isinstance(detalhes, dict) and nome_criterio in detalhes:
            detalhes[nome_criterio]['url_arquivo'] = None
            detalhes[nome_criterio]['evidencia_anexada'] = False
            supabase.table("monitorias").update({"detalhes": detalhes}).eq("id", id_monitoria).execute()

        detalhes_log = f"ID: {id_monitoria} | Critério: '{nome_criterio}' | Foto apagada manualmente."
        registrar_auditoria("REMOVER_EVIDENCIA", detalhes_log, sdr_afetado, nome_responsavel)
        
        get_all_records_db.clear()
        return True, "Foto apagada com sucesso!"
    except Exception as e: return False, str(e)