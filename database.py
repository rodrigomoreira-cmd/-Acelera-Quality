import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import pytz

# ==========================================================
# 🔌 INICIALIZAÇÃO E CONFIGURAÇÃO DE TIMEZONE
# ==========================================================
def obter_hora_brasil():
    """Retorna o horário atual formatado para o fuso de Brasília."""
    fuso = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso).isoformat()

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
        st.error(f"Erro Crítico de Conexão: {e}")
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
# 🕵️ SISTEMA CENTRAL DE AUDITORIA (LOG COMPLETO)
# ==========================================================

def registrar_auditoria(acao, colaborador_afetado, detalhes):
    """Grava log de ações no banco de dados com Timezone Correto."""
    if not supabase: return
    try:
        admin = st.session_state.get('user_nome', 'Sistema')
        hora_br = obter_hora_brasil()
        
        payload = {
            "admin_responsavel": admin,
            "colaborador_afetado": colaborador_afetado,
            "acao": acao,
            "detalhes": detalhes,
            "data_evento": hora_br,
            "criado_em": hora_br
        }
        supabase.table("auditoria").insert(payload).execute()
        get_all_records_db.clear() # Limpa cache para atualizar logs na tela
    except Exception as e:
        print(f"Falha ao registrar auditoria: {e}")

# ==========================================================
# 📝 MONITORIAS & NOTIFICAÇÕES
# ==========================================================

def salvar_monitoria_auditada(dados):
    """Salva monitoria, força data de Brasília e registra auditoria."""
    try:
        hora_br = obter_hora_brasil()
        dados['visualizada'] = False 
        dados['criado_em'] = hora_br # Força hora certa no banco
        
        response = supabase.table("monitorias").insert(dados).execute()
        get_all_records_db.clear()
        
        registrar_auditoria("MONITORIA REALIZADA", dados.get('sdr'), f"Nota: {dados.get('nota')}%")
        return True, "Monitoria salva com sucesso!"
    except Exception as e:
        return False, f"Erro ao salvar monitoria: {str(e)}"

def buscar_contagem_notificacoes(nome_usuario, nivel):
    """Calcula itens não lidos sem cache."""
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

def limpar_todas_notificacoes(nome_usuario):
    """Marca notificações como lidas."""
    try:
        supabase.table("monitorias").update({"visualizada": True}).eq("sdr", nome_usuario).execute()
        supabase.table("contestacoes").update({"visualizada": True}).eq("sdr_nome", nome_usuario).neq("status", "Pendente").execute()
        get_all_records_db.clear()
    except:
        pass

# ==========================================================
# 🔐 GESTÃO DE USUÁRIOS & SEGURANÇA (AUDITADO)
# ==========================================================

def criar_usuario_auditado(dados):
    """Cria usuário, valida duplicidade e gera log."""
    try:
        # Verifica duplicidade
        res = supabase.table("usuarios").select("user").eq("user", dados['user']).execute()
        if res.data:
            return False, "E-mail/Usuário já cadastrado."
        
        dados['criado_em'] = obter_hora_brasil()
        supabase.table("usuarios").insert(dados).execute()
        
        registrar_auditoria("CRIOU USUÁRIO", dados['nome'], f"Login: {dados['user']} | Nível: {dados['nivel']}")
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        return False, str(e)

def editar_usuario_auditado(user_login, dados_novos):
    """Edita dados de perfil e registra log."""
    try:
        supabase.table("usuarios").update(dados_novos).eq("user", user_login).execute()
        campos_alterados = ", ".join(dados_novos.keys())
        registrar_auditoria("EDITOU PERFIL", user_login, f"Campos alterados: {campos_alterados}")
        get_all_records_db.clear()
        return True, "Alterações salvas!"
    except Exception as e:
        return False, str(e)

def trocar_senha_auditado(user_login, nova_senha_hash, eh_admin=False):
    """Atualiza senha e identifica se foi reset de Admin ou troca própria."""
    try:
        supabase.table("usuarios").update({"password": nova_senha_hash}).eq("user", user_login).execute()
        
        acao = "ALTEROU SENHA (ADMIN)" if eh_admin else "ALTEROU PRÓPRIA SENHA"
        registrar_auditoria(acao, user_login, "Senha atualizada com sucesso.")
        return True, "Senha atualizada!"
    except Exception as e:
        return False, str(e)

# ==========================================================
# 🗑️ ANULAÇÃO & CONTESTAÇÃO (AUDITADO)
# ==========================================================

def anular_monitoria_auditada(id_monitoria, motivo):
    """Remove monitoria em cascata e gera log detalhado."""
    try:
        res_mon = supabase.table("monitorias").select("*").eq("id", id_monitoria).single().execute()
        if not res_mon.data: return False, "Monitoria não encontrada."
        
        sdr_afetado = res_mon.data.get('sdr')

        # Deleta contestações primeiro (Foreign Key)
        supabase.table("contestacoes").delete().eq("monitoria_id", id_monitoria).execute()
        # Deleta a monitoria
        supabase.table("monitorias").delete().eq("id", id_monitoria).execute()
        
        registrar_auditoria("ANULOU MONITORIA", sdr_afetado, f"ID: {id_monitoria} | Motivo: {motivo}")
        return True, "Anulada com sucesso."
    except Exception as e:
        return False, str(e)

def abrir_contestacao_auditada(payload):
    """SDR abre contestação."""
    try:
        payload['criado_em'] = obter_hora_brasil()
        supabase.table("contestacoes").insert(payload).execute()
        registrar_auditoria("ABRIU CONTESTAÇÃO", payload['sdr_nome'], f"Monitoria ID: {payload['monitoria_id']}")
        return True, "Contestação enviada!"
    except Exception as e:
        return False, str(e)

def responder_contestacao_auditada(id_cont, status, obs_admin, sdr_alvo):
    """Gestão responde a contestação."""
    try:
        payload = {
            "status": status,
            "resposta_admin": obs_admin,
            "data_resolucao": obter_hora_brasil(),
            "visualizada": False
        }
        supabase.table("contestacoes").update(payload).eq("id", id_cont).execute()
        registrar_auditoria(f"JULGOU CONTESTAÇÃO ({status})", sdr_alvo, f"ID: {id_cont}")
        return True, "Resposta enviada!"
    except Exception as e:
        return False, str(e)