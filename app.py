import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from time import sleep

# =========================================================
# 1. CONFIGURAÇÕES E CONEXÃO (SUPABASE)
# =========================================================

@st.cache_resource
def init_connection() -> Client:
    # O Streamlit procura automaticamente no secrets.toml pelos nomes abaixo
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
# Inicializa a conexão global (Singleton)
try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Erro ao conectar ao Supabase: {e}")
    st.stop()

# =========================================================
# 2. CONSTANTES E ESTILOS
# =========================================================
THEME = {
    "bg": "#111827", 
    "accent": "#ff7a00", 
    "card": "#1f2937", 
    "text": "#f3f4f6", 
    "error": "#f87171",
    "warning": "#facc15", 
    "success": "#4caf50"
}

ASSERTIVITY_CUTOFF = 85

# =========================================================
# 3. LÓGICA DE DADOS (DATABASE QUERIES)
# =========================================================

@st.cache_data(ttl=600)
def get_sdr_names_db():
    """Busca nomes de SDRs cadastrados na tabela 'sdrs'."""
    try:
        res = supabase.table("sdrs").select("nome").order("nome").execute()
        return [row['nome'] for row in res.data]
    except Exception as e:
        return []

def get_all_records_db(table="monitorias"):
    """Busca todos os registros de uma tabela e retorna como DataFrame."""
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

# =========================================================
# 4. SISTEMA DE AUTENTICAÇÃO
# =========================================================

def verificar_login(email, senha):
    """Valida credenciais na tabela 'usuarios'."""
    try:
        res = supabase.table("usuarios")\
            .select("nome_exibicao, nivel")\
            .eq("login_email", email)\
            .eq("senha", senha)\
            .eq("esta_ativo", True).execute()
        
        if res.data:
            st.session_state.authenticated = True
            st.session_state.user = res.data[0]['nome_exibicao']
            st.session_state.nivel = res.data[0]['nivel']
            return True
        return False
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return False

def render_login():
    st.title("🔐 Login - Acelera Quality")
    with st.form("login_form"):
        user = st.text_input("E-mail")
        pwd = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if verificar_login(user, pwd):
                st.rerun()
            else:
                st.error("Credenciais inválidas ou usuário inativo.")

# =========================================================
# 5. CÁLCULOS E REGRAS DE NEGÓCIO
# =========================================================

def calculate_score_details(checklist_model, checklist_state):
    """Calcula a nota final baseada nos pesos e Não Conformidades."""
    total_score = 100.0
    nc_items = []
    has_ncg = False
    
    for item in checklist_model:
        val = checklist_state.get(item["id"])
        weight = item["weight"] or 0
        if val in ['nc', 'nc_grave']:
            nc_items.append(item)
            total_score -= weight
            if val == 'nc_grave':
                has_ncg = True

    final_nota = 0.0 if has_ncg else max(0.0, total_score)
    return {"finalNota": final_nota, "ncCount": len(nc_items), "ncItems": nc_items, "hasNCG": has_ncg}

# =========================================================
# 6. COMPONENTES DE INTERFACE E SALVAMENTO
# =========================================================

def save_monitoria_record(score_details):
    """Envia o payload final para o Supabase."""
    form = st.session_state.monitoria_form
    
    payload = {
        "sdr": form['sdr'],
        "data": datetime.now().strftime('%Y-%m-%d'),
        "hora": datetime.now().strftime('%H:%M:%S'),
        "crm_link": form['crmLink'],
        "selene_link": form['seleneLink'],
        "nota": score_details['finalNota'],
        "observacoes": form['observacoes'],
        "plano_acao": form['planoAcaoMonitor'],
        "checklist_json": form['checklist']
    }

    try:
        supabase.table("monitorias").insert(payload).execute()
        st.success("✅ Monitoria enviada para o Supabase!")
        st.cache_data.clear() # Limpa cache do dashboard
        sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao subir dados para a nuvem: {e}")

def render_monitoria():
    st.title("📝 Nova Monitoria de Qualidade")
    
    if 'monitoria_form' not in st.session_state:
        st.session_state.monitoria_form = {
            'sdr': '', 'crmLink': '', 'seleneLink': '', 
            'checklist': {}, 'observacoes': '', 'planoAcaoMonitor': ''
        }

    nomes_sdr = get_sdr_names_db()

    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        st.session_state.monitoria_form['sdr'] = col1.selectbox("Selecione o SDR", [""] + nomes_sdr)
        st.session_state.monitoria_form['crmLink'] = col2.text_input("Link do CRM")
        st.session_state.monitoria_form['seleneLink'] = st.text_input("Link do Selene")
        
        st.divider()
        c1 = st.radio("O lead foi atendido em 15min?", ["conforme", "nc", "nc_grave"], horizontal=True)
        st.session_state.monitoria_form['checklist']['atendimento_15m'] = c1
        
        st.session_state.monitoria_form['observacoes'] = st.text_area("Observações")
        st.session_state.monitoria_form['planoAcaoMonitor'] = st.text_area("Plano de Ação")

        if st.form_submit_button("SALVAR NO SUPABASE"):
            if not st.session_state.monitoria_form['sdr']:
                st.error("Selecione o SDR antes de salvar.")
            else:
                model = [{"id": "atendimento_15m", "weight": 100}]
                score = calculate_score_details(model, st.session_state.monitoria_form['checklist'])
                save_monitoria_record(score)

def render_dashboard():
    st.title("📊 Dashboard de Performance")
    df = get_all_records_db()
    
    if df.empty:
        st.warning("Sem dados para exibir.")
        return

    if st.session_state.nivel == 'sdr':
        df = df[df['sdr'] == st.session_state.user]

    c1, c2, c3 = st.columns(3)
    avg = df['nota'].mean()
    c1.metric("Média de Assertividade", f"{avg:.2f}%")
    c2.metric("Total de Monitorias", len(df))
    c3.metric("NC Graves", len(df[df['nota'] == 0]))

    df['data'] = pd.to_datetime(df['data'])
    trend = df.groupby('data')['nota'].mean().reset_index()
    fig = px.line(trend, x='data', y='nota', title="Evolução das Notas", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 7. EXECUÇÃO PRINCIPAL
# =========================================================

def main():
    st.set_page_config(layout="wide", page_title="Acelera Quality")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        render_login()
        st.stop()

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.write(f"Nível: {st.session_state.nivel.upper()}")
        st.divider()
        page = st.radio("Navegação", ["DASHBOARD", "MONITORIA", "HISTÓRICO", "CADASTRO"])
        st.divider()
        if st.button("🚪 Sair"):
            st.session_state.authenticated = False
            st.rerun()

    if page == "DASHBOARD": 
        render_dashboard()
    elif page == "MONITORIA": 
        render_monitoria()
    elif page == "HISTÓRICO":
        st.title("📜 Histórico")
        df = get_all_records_db()
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()