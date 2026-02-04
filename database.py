import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ==========================================================
# 🔌 INICIALIZAÇÃO GLOBAL (CACHE DE CONEXÃO)
# ==========================================================
@st.cache_resource
def init_connection():
    """Inicializa a conexão única com o Supabase."""
    try:
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
# 📥 FUNÇÕES DE LEITURA (COM CACHE)
# ==========================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_all_records_db(tabela):
    """Busca registros com cache de 60 segundos para performance."""
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(tabela).select("*").order("criado_em", desc=True).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        print(f"Erro ao buscar {tabela}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_criterios_ativos():
    """Busca critérios ativos com cache de 5 minutos."""
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table("config_criterios").select("*").eq("ativo", True).execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# ==========================================================
# 🔔 NOTIFICAÇÕES (TEMPO REAL)
# ==========================================================

def buscar_contagem_notificacoes(nome_usuario, nivel):
    """Calcula itens não lidos sem cache para precisão imediata."""
    if not nome_usuario or nome_usuario == "Usuário" or not supabase:
        return 0
    try:
        if nivel == "SDR":
            res_mon = supabase.table("monitorias").select("id", count="exact")\
                .eq("sdr", nome_usuario).eq("visualizada", False).execute()
            res_cont = supabase.table("contestacoes").select("id", count="exact")\
                .eq("sdr_nome", nome_usuario).neq("status", "Pendente").eq("visualizada", False).execute()
            return (res_mon.count or 0) + (res_cont.count or 0)
        elif nivel in ["ADMIN", "GESTAO"]:
            res = supabase.table("contestacoes").select("id", count="exact")\
                .eq("status", "Pendente").execute()
            return res.count or 0
    except:
        return 0

# ==========================================================
# 📤 FUNÇÕES DE ESCRITA E AUDITORIA
# ==========================================================

def registrar_auditoria(acao, colaborador_afetado, detalhes):
    """Grava log de ações no banco de dados."""
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
    except:
        pass

def save_monitoria(dados):
    """Salva nova monitoria e limpa o cache de leitura."""
    try:
        dados['visualizada'] = False 
        response = supabase.table("monitorias").insert(dados).execute()
        get_all_records_db.clear()
        registrar_auditoria("MONITORIA REALIZADA", dados.get('sdr'), f"Nota: {dados.get('nota')}%")
        return response
    except Exception as e:
        st.error(f"Erro ao salvar monitoria.")
        raise e

def limpar_todas_notificacoes(nome_usuario):
    """Marca notificações como lidas e limpa o cache."""
    try:
        supabase.table("monitorias").update({"visualizada": True}).eq("sdr", nome_usuario).execute()
        supabase.table("contestacoes").update({"visualizada": True}).eq("sdr_nome", nome_usuario).neq("status", "Pendente").execute()
        get_all_records_db.clear()
    except:
        pass

# ==========================================================
# 🗑️ FUNÇÃO DE ANULAÇÃO (CORRIGIDA)
# ==========================================================
def anular_monitoria(id_monitoria, motivo):
    """
    Remove uma monitoria e suas contestações, registrando tudo na auditoria.
    """
    try:
        # 1. Busca dados da monitoria para o log
        res_mon = supabase.table("monitorias").select("*").eq("id", id_monitoria).single().execute()
        if not res_mon.data:
            return False, "Monitoria não encontrada."
        
        dados_mon = res_mon.data

        # 2. Verifica se existem contestações vinculadas para detalhar na auditoria
        res_cont = supabase.table("contestacoes").select("id").eq("monitoria_id", id_monitoria).execute()
        tem_contestacao = len(res_cont.data) > 0
        qtd_cont = len(res_cont.data)

        # 3. DELEÇÃO EM CASCATA MANUAL
        # Primeiro as contestações (filhos)
        if tem_contestacao:
            supabase.table("contestacoes").delete().eq("monitoria_id", id_monitoria).execute()
        
        # Depois a monitoria (pai)
        supabase.table("monitorias").delete().eq("id", id_monitoria).execute()
        
        # 4. REGISTRO DE AUDITORIA COMPLETO
        detalhe_final = f"ID: {id_monitoria} | Motivo: {motivo}"
        if tem_contestacao:
            detalhe_final += f" | ⚠️ OBS: {qtd_cont} contestação(ões) vinculada(s) também foi(ram) excluída(s)."

        registrar_auditoria(
            acao="ANULOU MONITORIA",
            colaborador_afetado=dados_mon.get('sdr'),
            detalhes=detalhe_final
        )
        
        # 5. Limpa Cache
        get_all_records_db.clear()
        
        return True, "Monitoria (e contestações vinculadas) anuladas com sucesso."
    
    except Exception as e:
        return False, f"Erro ao anular: {str(e)}"