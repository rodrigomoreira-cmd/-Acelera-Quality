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

def registrar_auditoria(acao, admin_nome, detalhes, afetado=None):
    """
    Registra uma ação no banco de dados para segurança e rastreio.
    """
    try:
        fuso_br = pytz.timezone('America/Sao_Paulo')
        hora_agora = datetime.now(fuso_br).isoformat()
        
        payload = {
            "data_evento": hora_agora,
            "acao": acao,
            "admin_responsavel": admin_nome,
            "detalhes": detalhes,
            "colaborador_afetado": afetado or "N/A"
        }
        
        supabase.table("auditoria").insert(payload).execute()
        get_all_records_db.clear()
        
        return True
    except Exception as e:
        print(f"❌ ERRO CRÍTICO AO SALVAR AUDITORIA: {e}")
        return False

# ==========================================================
# 📝 MONITORIAS & NOTIFICAÇÕES
# ==========================================================

def salvar_monitoria_auditada(dados):
    """Salva monitoria e registra auditoria com Responsável e Afetado corretos."""
    try:
        hora_br = obter_hora_brasil()
        dados['visualizada'] = False 
        dados['criado_em'] = hora_br 
        
        supabase.table("monitorias").insert(dados).execute()
        get_all_records_db.clear()
        
        # AJUSTE: O responsável é o monitor, o afetado é o SDR
        monitor = dados.get('monitor_responsavel', 'Sistema')
        sdr_alvo = dados.get('sdr', 'N/A')
        
        registrar_auditoria(
            acao="MONITORIA REALIZADA", 
            admin_nome=monitor, 
            detalhes=f"Nota: {dados.get('nota')}%", 
            afetado=sdr_alvo
        )
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
    """Cria usuário e registra quem foi o administrador responsável."""
    try:
        res = supabase.table("usuarios").select("user").eq("user", dados['user']).execute()
        if res.data:
            return False, "E-mail/Usuário já cadastrado."
        
        dados['criado_em'] = obter_hora_brasil()
        supabase.table("usuarios").insert(dados).execute()
        
        # AJUSTE: Pegar o nome do admin logado da sessão
        admin_logado = st.session_state.get('user_nome', 'Admin')
        
        registrar_auditoria(
            acao="CRIOU USUÁRIO", 
            admin_nome=admin_logado, 
            detalhes=f"Login: {dados['user']} | Nível: {dados['nivel']}",
            afetado=dados['nome']
        )
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        return False, str(e)

def editar_usuario_auditado(user_login, dados_novos):
    """Edita dados de perfil e registra log."""
    try:
        supabase.table("usuarios").update(dados_novos).eq("user", user_login).execute()
        campos_alterados = ", ".join(dados_novos.keys())
        admin_logado = st.session_state.get('user_nome', user_login)
        
        registrar_auditoria("EDITOU PERFIL", admin_logado, f"Campos alterados: {campos_alterados}", afetado=user_login)
        get_all_records_db.clear()
        return True, "Alterações salvas!"
    except Exception as e:
        return False, str(e)

def trocar_senha_auditado(user_login, nova_senha_hash, eh_admin=False):
    """Atualiza senha e identifica se foi reset de Admin ou troca própria."""
    try:
        supabase.table("usuarios").update({"senha": nova_senha_hash}).eq("user", user_login).execute()
        admin_logado = st.session_state.get('user_nome', user_login)
        
        acao = "ALTEROU SENHA (ADMIN)" if eh_admin else "ALTEROU PRÓPRIA SENHA"
        registrar_auditoria(acao, admin_logado, "Senha atualizada com sucesso.", afetado=user_login)
        return True, "Senha atualizada!"
    except Exception as e:
        return False, str(e)

# ==========================================================
# 🗑️ ANULAÇÃO & CONTESTAÇÃO (AUDITADO)
# ==========================================================

def anular_monitoria_auditada(id_monitoria, motivo, nome_responsavel):
    """Remove monitoria em cascata e registra o Admin responsável."""
    try:
        res_mon = supabase.table("monitorias").select("*").eq("id", id_monitoria).single().execute()
        if not res_mon.data: return False, "Monitoria não encontrada."
        
        sdr_afetado = res_mon.data.get('sdr', 'N/A')

        supabase.table("contestacoes").delete().eq("monitoria_id", id_monitoria).execute()
        supabase.table("monitorias").delete().eq("id", id_monitoria).execute()
        
        registrar_auditoria(
            acao="ANULAR_MONITORIA", 
            admin_nome=nome_responsavel, 
            detalhes=f"ID: {id_monitoria} | Motivo: {motivo}", 
            afetado=sdr_afetado
        )
        return True, "Anulada com sucesso."
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
        admin_logado = st.session_state.get('user_nome', 'Admin')
        supabase.table("contestacoes").update(payload).eq("id", id_cont).execute()
        
        registrar_auditoria(
            acao=f"JULGOU CONTESTAÇÃO ({status})", 
            admin_nome=admin_logado, 
            detalhes=f"ID Contestação: {id_cont}", 
            afetado=sdr_alvo
        )
        return True, "Resposta enviada!"
    except Exception as e:
        return False, str(e)