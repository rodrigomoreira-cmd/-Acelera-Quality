import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ==========================================================
# 🔌 INICIALIZAÇÃO GLOBAL (CACHE DE CONEXÃO)
# ==========================================================
@st.cache_resource
def init_connection():
    """
    Inicializa a conexão com o Supabase.
    @st.cache_resource garante que conectamos apenas UMA vez ao iniciar o app.
    """
    try:
        # Tenta pegar dos secrets, se não der, retorna None
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro Crítico: Verifique as chaves SUPABASE no secrets.toml.")
        return None

supabase = init_connection()

# ==========================================================
# 📥 FUNÇÕES DE LEITURA (COM CACHE INTELIGENTE)
# ==========================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_all_records_db(tabela):
    """
    Busca registros e guarda em cache por 60 segundos.
    Isso evita que cada clique no dashboard consuma o banco de dados.
    """
    if not supabase: return pd.DataFrame()
    
    try:
        # Busca ordenada para garantir que os gráficos mostrem cronologia correta
        res = supabase.table(tabela).select("*").order("criado_em", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        print(f"Erro ao buscar {tabela}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300) # Cache longo (5 min) pois critérios mudam pouco
def get_criterios_ativos():
    """Busca critérios configurados como ativos."""
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table("config_criterios").select("*").eq("ativo", True).execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# ==========================================================
# 🔔 FUNÇÕES DE NOTIFICAÇÃO (SEM CACHE - TEMPO REAL)
# ==========================================================

def buscar_contagem_notificacoes(nome_usuario, nivel):
    """Calcula o número de itens não lidos para o Badge."""
    if not nome_usuario or nome_usuario == "Usuário" or not supabase:
        return 0
        
    try:
        if nivel == "SDR":
            # 1. Monitorias Novas
            res_mon = supabase.table("monitorias").select("id", count="exact")\
                .eq("sdr", nome_usuario).eq("visualizada", False).execute()
            
            # 2. Respostas de Contestação
            res_cont = supabase.table("contestacoes").select("id", count="exact")\
                .eq("sdr_nome", nome_usuario).neq("status", "Pendente").eq("visualizada", False).execute()
            
            count_mon = res_mon.count if res_mon.count else 0
            count_cont = res_cont.count if res_cont.count else 0
            
            return count_mon + count_cont
            
        elif nivel in ["ADMIN", "GESTAO"]:
            # Admin/Gestão veem contestações Pendentes
            res = supabase.table("contestacoes").select("id", count="exact")\
                .eq("status", "Pendente").execute()
            return res.count if res.count else 0
            
    except Exception as e:
        print(f"Erro notificações: {e}")
        return 0

# ==========================================================
# 📤 FUNÇÕES DE ESCRITA E DELEÇÃO (SEM CACHE)
# ==========================================================

def registrar_auditoria(acao, colaborador_afetado, detalhes):
    """Grava logs de segurança."""
    if not supabase: return
    try:
        admin = st.session_state.get('user_nome', 'Sistema')
        payload = {
            "admin_responsavel": admin,
            "colaborador_afetado": colaborador_afetado,
            "acao": acao,
            "detalhes": detalhes,
            "data_evento": datetime.now().isoformat()
        }
        supabase.table("auditoria").insert(payload).execute()
    except Exception as e:
        print(f"Erro auditoria: {e}")

def save_monitoria(dados):
    """Salva a monitoria e dispara o registro de auditoria."""
    try:
        dados['visualizada'] = False 
        response = supabase.table("monitorias").insert(dados).execute()
        
        # Limpa o cache para que o dashboard atualize imediatamente
        get_all_records_db.clear()
        
        registrar_auditoria(
            acao="MONITORIA REALIZADA", 
            colaborador_afetado=dados.get('sdr'), 
            detalhes=f"Nota: {dados.get('nota')}% | Monitor: {dados.get('monitor_responsavel')}"
        )
        return response
    except Exception as e:
        st.error(f"Erro ao salvar monitoria: {e}")
        raise e

def limpar_todas_notificacoes(nome_usuario):
    """Marca TUDO como lido."""
    try:
        # 1. Monitorias
        supabase.table("monitorias").update({"visualizada": True})\
            .eq("sdr", nome_usuario).eq("visualizada", False).execute()
            
        # 2. Contestações
        supabase.table("contestacoes").update({"visualizada": True})\
            .eq("sdr_nome", nome_usuario).neq("status", "Pendente").eq("visualizada", False).execute()
            
        # Limpa cache para refletir a mudança visual
        get_all_records_db.clear()
    except Exception as e:
        print(f"Erro limpar notificações: {e}")


def anular_monitoria(id_monitoria, motivo):
    """
    Remove uma monitoria do banco de dados e registra na auditoria.
    """
    try:
        # 1. Busca dados antes de apagar para o log (Auditoria)
        res = supabase.table("monitorias").select("*").eq("id", id_monitoria).single().execute()
        if not res.data:
            return False, "Monitoria não encontrada."
        
        dados = res.data
        
        # --- CORREÇÃO AQUI ---
        # Ordem Invertida: Primeiro apagamos os FILHOS (Contestações)
        # Se não fizermos isso, o banco bloqueia a exclusão do PAI (Monitoria)
        supabase.table("contestacoes").delete().eq("monitoria_id", id_monitoria).execute()
        
        # 2. Agora sim, apagamos o PAI (Monitoria)
        supabase.table("monitorias").delete().eq("id", id_monitoria).execute()
        
        # 3. Auditoria
        registrar_auditoria(
            acao="ANULOU MONITORIA",
            colaborador_afetado=dados.get('sdr'),
            detalhes=f"ID {id_monitoria} deletado. Motivo: {motivo}"
        )
        
        # 4. Limpa Cache
        get_all_records_db.clear()
        
        return True, "Monitoria anulada com sucesso."
    except Exception as e:
        # Pega erro detalhado do Supabase se houver
        err_msg = str(e)
        if "foreign key constraint" in err_msg:
            return False, "Erro de vínculo: Existem contestações ativas que impedem a exclusão."
        return False, err_msg