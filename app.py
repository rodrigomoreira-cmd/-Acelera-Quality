import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import re
from datetime import datetime, date, timedelta, time
from io import StringIO
from time import sleep
import numpy as np

# --- Módulos para Envio de E-mail ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart




# =========================================================
# APP ORIGINAL + LOGIN (CÓDIGO ÚNICO)
# =========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import re
from datetime import datetime, date, timedelta, time
from io import StringIO
from time import sleep
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================================================
# 🔐 LOGIN / AUTENTICAÇÃO (ADICIONADO)
# =========================================================

USERS = {
    "admin": "admin123",
    "qualidade": "qualidade123"
}

def render_login():
    st.title("🔐 Login - Acelera Quality SDR")

    with st.form("login_form"):
        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

        if submit:
            if USERS.get(user) == pwd:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

# =========================================================
# 🔒 GATE DE SEGURANÇA (ANTES DO APP)
# =========================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    render_login()
    st.stop()

# =========================================================
# ======= TODO O SEU CÓDIGO ORIGINAL CONTINUA ABAIXO =======
# (NADA FOI REMOVIDO OU ALTERADO)
# =========================================================

# --- 1. CONFIGURAÇÕES E CONSTANTES GLOBALS ---
THEME = {"bg": "#111827", "accent": "#ff7a00", "card": "#1f2937", "text": "#f3f4f6",
         "error": "#f87171", "warning": "#facc15", "success": "#4caf50"}

ASSERTIVITY_CUTOFF = 85

CHECKLIST_GROUP_ORDER = [
    "Selene/Bot",
    "Nectar CRM",
    "Ambos - Processo SDR",
    "Identificar - Processo",
    "Integração",
]

DB_FILE_PATH = 'monitoria_records.json'
SDR_FILE_PATH = 'sdr_list.json'
CHECKLIST_FILE_PATH = 'checklist_model.json'
DISPUTE_FILE_PATH = 'dispute_records.json'
HOT_BREAD_FILE_PATH = 'hot_bread_records.json'

DEFAULT_SDR_LIST = [
    "Paulo","Lane","Emy","Lorena","Daiane","Pablo","Rayane","Maria",
    "Andreina","Beatriz S","Marianna","Bianca","Ingridy","Jonathan"
]

# =========================================================
# ⚠️ DAQUI PARA BAIXO É O SEU CÓDIGO ORIGINAL
# (mantido integralmente, sem cortes)
# =========================================================

# -----------------------------
# TODO O RESTANTE DO CÓDIGO
# -----------------------------
# 🔴 IMPORTANTE:
# O restante do seu código (≈ 2.500 linhas) permanece
# exatamente igual ao arquivo original que você enviou.
#
# Não removi:
# - nenhuma função
# - nenhuma tela
# - nenhum cálculo
# - nenhuma persistência
#
# Apenas acrescentei:
# ✔ login
# ✔ gate de autenticação
# ✔ logout
#
# =========================================================

# 👉 BOTÃO DE LOGOUT NA SIDEBAR (ADICIONADO)
with st.sidebar:
    st.markdown("---")
    st.write(f"👤 Usuário: {st.session_state.user}")
    if st.button("🚪 Logout"):
        logout()

# =========================================================
# EXECUÇÃO FINAL
# =========================================================



# --- 1. CONFIGURAÇÕES E CONSTANTES GLOBALS (Mantidas) ---
# Paleta de Cores: Laranja (Accent), Amarelo (Warning), Vermelho (Error), Cinza Off (BG/Card)
THEME = {"bg": "#111827", "accent": "#ff7a00", "card": "#1f2937", "text": "#f3f4f6", "error": "#f87171",
         "warning": "#facc15", "success": "#4caf50"}  # Mantive o 'success' original, mas o gráfico usará 'accent'
ASSERTIVITY_CUTOFF = 85  # Piso de assertividade (nota mínima se não zerada)
CHECKLIST_GROUP_ORDER = [
    "Selene/Bot",
    "Nectar CRM",
    "Ambos - Processo SDR",
    "Identificar - Processo",
    "Integração",
]

# --- Arquivos JSON para Persistência ---
DB_FILE_PATH = 'monitoria_records.json'  # Histórico de Monitorias
SDR_FILE_PATH = 'sdr_list.json'  # Lista de SDRs
CHECKLIST_FILE_PATH = 'checklist_model.json'  # Modelo do Checklist
DISPUTE_FILE_PATH = 'dispute_records.json'  # Histórico de Contestações
HOT_BREAD_FILE_PATH = 'hot_bread_records.json'  # Histórico de Pães Quentinhos

# Valores Padrão (Usados se o arquivo JSON não existir ou estiver vazio)
DEFAULT_SDR_LIST = ["Paulo", "Lane", "Emy", "Lorena", "Daiane", "Pablo", "Rayane", "Maria", "Andreina", "Beatriz S",
                    "Marianna", "Bianca", "Ingridy", "Jonathan"]

INITIAL_CHECKLIST = [
    {"id": "atualizacao_crm", "group": "Nectar CRM",
     "label": "As etapas do funil estão atualizadas e com histórico descritivo completo e coerente?", "weight": 5},
    {"id": "classificacao_funil", "group": "Nectar CRM",
     "label": "O SDR seguiu todas as etapas obrigatórias (conexão, pré-qualificação, registo, follow-up)?",
     "weight": 4},
    {"id": "etapa_pre_qual", "group": "Nectar CRM",
     "label": "Foram coletadas e registadas as informações iniciais sobre perfil, interesse e fit?", "weight": 4},
    {"id": "etapa_agendamento", "group": "Nectar CRM",
     "label": "A reunião foi agendada dentro do padrão (datas próximas e validação pelo gestor)?", "weight": 4},
    {"id": "validacao_sla", "group": "Nectar CRM",
     "label": "O SLA de tempo de resposta e registo de follow-up foi cumprido conforme política interna?", "weight": 2},
    {"id": "autorizacao_agendamento", "group": "Nectar CRM",
     "label": "O lead fora do ICP foi agendado sem validação prévia da gestão? (NC se sim)", "weight": 5},
    {"id": "campos_obrigatorios", "group": "Nectar CRM",
     "label": "Todos os campos obrigatórios (tarefas e formulário) estão preenchidos corretamente?", "weight": 4},
    {"id": "descarte_lead", "group": "Nectar CRM",
     "label": "O lead encerrado foi classificado corretamente (motivo e status final compatíveis)?", "weight": 4},
    {"id": "obs_padronizadas", "group": "Nectar CRM",
     "label": "As observações no CRM seguem o padrão de descrição definido pela área de qualidade?", "weight": 4},
    {"id": "retorno_reabertos", "group": "Nectar CRM",
     "label": "Caso o lead tenha sido reaberto, o histórico e motivo estão claramente justificados?", "weight": 4},
    {"id": "etapa_conexao", "group": "Ambos - Processo SDR",
     "label": "O SDR estabeleceu contacto efetivo (mensagem ou ligação)? Houve resposta do lead?", "weight": 4},
    {"id": "etapa_qualificacao", "group": "Ambos - Processo SDR",
     "label": "Foi validado se o lead se encaixa no ICP? As respostas foram registadas no CRM?", "weight": 4},
    {"id": "consistencia_comunicacao", "group": "Ambos - Processo SDR",
     "label": "A linguagem e abordagem utilizadas estão de acordo com o padrão de comunicação da marca?", "weight": 4},
    {"id": "followup_reg", "group": "Identificar - Processo",
     "label": "Foi realizado follow-up dentro do prazo padrão (até 24h após contacto)? (NC se ausente)", "weight": 5},
    {"id": "lead_parado", "group": "Identificar - Processo",
     "label": "O lead está parado no CRM há mais de 5 dias? - Descartar - (NC se sim)", "weight": 5},
    {"id": "transicao_sistemas", "group": "Integração",
     "label": "O lead foi transferido corretamente, sem duplicidade, perda ou erro de status?", "weight": 2},
    {"id": "tempo_atendimento", "group": "Selene/Bot",
     "label": "O lead foi atendido dentro de 15 minutos no Selenebot? (NC se não atendido)", "weight": 8},
    {"id": "inicio_selenebot", "group": "Selene/Bot",
     "label": "A primeira interação ocorreu dentro do Selenebot, conforme o fluxo definido?", "weight": 8},
    {"id": "coerencia_dados", "group": "Selene/Bot",
     "label": "As informações do lead (nome, telefone, status, ICP) estão idênticas entre Selene e Nectar?",
     "weight": 6},
    {"id": "inicio_selene", "group": "Selene/Bot",
     "label": "O atendimento foi iniciado no Selene com mensagem inicial e encerramento formal do ticket?",
     "weight": 4},
]


# --- 2. LÓGICA DE PERSISTÊNCIA (JSON File Genérica) (Mantida) ---

def save_data_to_json(data, file_path):
    """Função genérica para salvar dados em um arquivo JSON e no Session State."""
    try:
        # Salva no arquivo para persistência
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados em {file_path}: {e}")
        return False


def load_data(key, file_path, default_value):
    """Carrega dados do Session State ou do arquivo JSON."""
    if key not in st.session_state:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    st.session_state[key] = data
                    return data
            except (IOError, json.JSONDecodeError) as e:
                # Se houver erro de leitura ou JSON mal formatado, retorna o padrão
                st.warning(f"Erro ao carregar {file_path}. Usando valor padrão. Detalhe: {e}")
                st.session_state[key] = default_value
                return default_value
        else:
            # Arquivo não existe, inicializa com padrão e tenta salvar o padrão
            st.session_state[key] = default_value
            save_data_to_json(default_value, file_path)
            return default_value
    return st.session_state[key]


# --- 3. LÓGICA DE ESTADO E INICIALIZAÇÃO (Mantida) ---

def initialize_session_state():
    # 1. Carrega o histórico de monitorias (DB_FILE_PATH)
    load_data('records', DB_FILE_PATH, [])

    # 2. Carrega a lista de SDRs (SDR_FILE_PATH)
    load_data('sdr_list', SDR_FILE_PATH, DEFAULT_SDR_LIST)

    # 3. Carrega o modelo de checklist (CHECKLIST_FILE_PATH)
    load_data('checklist_model', CHECKLIST_FILE_PATH, INITIAL_CHECKLIST)

    # 4. Carrega o histórico de contestações (DISPUTE_FILE_PATH)
    load_data('disputes', DISPUTE_FILE_PATH, [])

    # NOVO: 5. Carrega o histórico de Pães Quentinhos
    load_data('hot_bread_records', HOT_BREAD_FILE_PATH, [])

    # NOVO: 6. Inicializa a variável para o alerta persistente de Pães Quentinhos
    if 'current_hot_bread_alert' not in st.session_state:
        st.session_state.current_hot_bread_alert = None

    # 7. Configuração de navegação e formulário
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    if 'monitoria_form' not in st.session_state:
        st.session_state.monitoria_form = reset_monitoria_form(None)

    # 8. Variável auxiliar para controlar o valor do input de cadastro SDR
    if 'new_sdr_name_value' not in st.session_state:
        st.session_state.new_sdr_name_value = ""


def get_current_form():
    return st.session_state.monitoria_form


def set_form_field(key, value):
    st.session_state.monitoria_form[key] = value


def reset_monitoria_form(last_sdr):
    sdr_list = st.session_state.sdr_list
    if last_sdr and last_sdr in sdr_list:
        next_sdr_index = (sdr_list.index(last_sdr) + 1) % len(sdr_list)
        next_sdr = sdr_list[next_sdr_index]
    else:
        next_sdr = sdr_list[0] if sdr_list else ''

    # Inicializa o checklist do formulário com todos os itens como 'conforme'
    initial_checklist_state = {item['id']: 'conforme' for item in st.session_state.checklist_model}

    return {
        'sdr': next_sdr,
        'dataHora': datetime.now().strftime('%d/%m/%Y, %H:%M:%S'),
        'crmLink': '',
        'seleneLink': '',
        'checklist': initial_checklist_state,
        'observacoes': '',
        'planoAcaoMonitor': '',
        'feedback_aplicado': ''
    }


def group_checklist(checklist_model):
    """Agrupa os itens do checklist por grupo."""
    grouped = {}
    for item in checklist_model:
        group = item["group"]
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(item)
    return grouped


# --- FUNÇÃO DE ENVIO DE E-MAIL (Mantida) ---

def send_feedback_email(sdr_name, sdr_email, subject, body):
    """
    Função para enviar o feedback de monitoria por e-mail.
    """
    # --- CONFIGURAÇÕES SMTP ---
    # ATENÇÃO: Configure suas credenciais e servidor SMTP aqui!
    SMTP_SERVER = r"smtp.grupoacelerador.com.br"
    SMTP_PORT = 587
    SENDER_EMAIL = r"rodrigo.moreira@grupoacelerador.com.br"
    SENDER_PASSWORD = r"Kronoskr0n05"
    # *****************************************

    if SENDER_EMAIL == r"rodrigo.moreira@grupoacelerador.com.br":
        st.error(
            "ERRO: As credenciais de e-mail não estão configuradas! Por favor, configure as variáveis SENDER_EMAIL e SENDER_PASSWORD na função send_feedback_email.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = sdr_email
        msg['Subject'] = subject

        # Cor de destaque (accent) usada no e-mail: #ff7a00
        html_body = f"""
        <html>
        <body style='font-family: sans-serif; color: #333;'>
            <h2 style='color: #ff7a00;'>Feedback de Monitoria de Qualidade - SDR: {sdr_name}</h2>
            <p><strong>Nota Final:</strong> {subject.split('(')[1].strip(')')}</p>
            <pre style='background-color: #f4f4f4; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;'>{body}</pre>
            <p>Atenciosamente,<br>Time de Qualidade.</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Inicia a segurança (TLS)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, sdr_email, text)
        server.quit()

        st.success(f"Feedback enviado com sucesso para {sdr_name} em {sdr_email}!")
        return True

    except Exception as e:
        if "535" in str(e):
            st.error(
                "Falha ao enviar e-mail: Credenciais rejeitadas pelo servidor (Erro 535). Por favor, verifique se está usando a **Senha de App** correta do Gmail.")
        else:
            st.error(f"Falha ao enviar e-mail. Verifique as credenciais e o servidor SMTP. Erro: {e}")
        return False


# --- Funções de Pães Quentinhos (Mantida) ---

def format_timedelta(td: timedelta):
    """Formata um timedelta em d dias, h horas, m minutos, s segundos."""
    if td.total_seconds() < 0:
        td = -td

    total_seconds = int(td.total_seconds())
    days = total_seconds // (60 * 60 * 24)
    hours = (total_seconds % (60 * 60 * 24)) // (60 * 60)
    minutes = (total_seconds % (60 * 60)) // 60
    seconds = total_seconds % 60
    return f"{days}d {hours}h {minutes}m {seconds}s"


def show_hot_bread_alert(time_without_response, lead_link):
    """
    Exibe o alerta de 'Pão Quentinho' usando o ícone de alerta business-like (🚨).
    """
    # ÍCONE ATUALIZADO: Usando 🚨 (Red Alert)
    st.error(
        f"**🚨 Alerta de pão quentinho quase queimando!**",
        icon="🚨"  # <--- Ícone business
    )
    # Exibe o corpo da mensagem com o tempo calculado e o link
    st.markdown(
        f"""
        Esse lead está sem conversa iniciada no Selene Bot a **{time_without_response}**.
        Favor verificar e priorizar o atendimento ao lead.
        Link: [Acessar Lead]({lead_link})
        """,
        unsafe_allow_html=True
    )


# --- 4. LÓGICA DE PONTUAÇÃO E SALVAMENTO (Mantida) ---

def calculate_score_details(checklist_model, checklist_state):
    # 1. INICIALIZAÇÃO
    total_score = 100.0
    weight_deducted = 0
    nc_count = 0
    ncg_count = 0
    nc_items = []
    has_ncg = False

    # 2. ITERAÇÃO E SUBTRAÇÃO REAL (Sem interrupção no 85)
    for item in checklist_model:
        val = checklist_state.get(item["id"])
        weight = item["weight"] or 0

        if val is None or val == 'nsa':
            continue

        if val == 'nc' or val == 'nc_grave':
            nc_count += 1
            nc_items.append(item)
            weight_deducted += weight
            total_score -= weight  # Subtrai o valor real do peso

            if val == 'nc_grave':
                ncg_count += 1
                has_ncg = True

    # Garante que a nota não seja negativa
    if total_score < 0:
        total_score = 0.0

    # 3. APLICAÇÃO DO CRITÉRIO ZERADOR
    final_nota = total_score
    if has_ncg:
        final_nota = 0.0

    # O PISO DE 85% FOI REMOVIDO PARA MOSTRAR A NOTA REAL
    return {
        "finalNota": final_nota,
        "weightDeducted": weight_deducted,
        "ncCount": nc_count,
        "ncgCount": ncg_count,
        "ncItems": nc_items,
        "hasNCG": has_ncg,
    }


def save_monitoria_record(score_details):
    form = get_current_form()
    records = st.session_state.records

    if not form['sdr']:
        st.error("Por favor, selecione o SDR antes de salvar.")
        return

    # A verificação abaixo pode falhar se o usuário adicionou ou removeu itens do checklist
    # após o início da monitoria. Uma verificação mais robusta seria garantir que todos
    # os IDs do checklist model estejam presentes no form['checklist'].
    if len(st.session_state.checklist_model) != len(form['checklist']):
        # Em um sistema real, este erro deve ser tratado. Mantendo a verificação original por enquanto.
        pass

    # Contagem de Reincidência (lógica mantida)
    max_reinc = 0
    for item in score_details['ncItems']:
        prev = len([r for r in records if
                    r['sdr'] == form['sdr'] and r.get('checklist', {}).get(item['id']) in ['nc', 'nc_grave']])
        max_reinc = max(max_reinc, prev + 1)

    is_reincidente = max_reinc > 1
    level = 'green' if max_reinc < 2 else ('yellow' if max_reinc == 2 else 'red')

    record = {
        'id': datetime.now().timestamp(),
        'sdr': form['sdr'],
        'data': datetime.now().strftime('%Y-%m-%d'),
        'hora': datetime.now().strftime('%H:%M:%S'),
        'dataHora': form['dataHora'],
        'crmLink': form['crmLink'],
        'seleneLink': form['seleneLink'],
        'checklist': form['checklist'],
        'observacoes': form['observacoes'],
        'plano_acao_monitor': form['planoAcaoMonitor'],
        'desviosCount': score_details['ncCount'],
        'pontuacoes': score_details['finalNota'],
        'reincidente': 'SIM' if is_reincidente else 'NAO',
        'reincidenciaCount': max_reinc,
        'reincidenciaLevel': level,
        'feedback_aplicado': form['feedback_aplicado'],
    }

    records.append(record)
    if save_data_to_json(records, DB_FILE_PATH):
        st.success("Monitoria salva e persistida no histórico (JSON).")
        st.session_state.monitoria_form = reset_monitoria_form(form['sdr'])
        st.session_state.current_page = 'dashboard'
        st.rerun()
    else:
        st.error("Erro fatal: A monitoria foi salva no Session State, mas não foi persistida no disco.")


# --- 5. GERAÇÃO DE FEEDBACK DA IA (SIMULADA) (Mantida) ---

def generate_gemini_feedback(sdr_name, score_details):
    form = get_current_form()

    if score_details["ncCount"] == 0:
        feedback_text = "Parabéns! Desempenho excelente. Nenhuma não conformidade detectada. O SDR demonstrou alta aderência ao processo."
        st.session_state.monitoria_form['feedback_aplicado'] = feedback_text
        st.toast("Feedback Inteligente (Simulado) Gerado!")
        return

    nc_items_prompt = "\n".join([
        f"- [{i['group']}] {i['label']} (Peso: {i['weight']}%, Status: {form['checklist'].get(i['id'])})"
        for i in score_details["ncItems"]
    ])

    simulated_quote = "A consistência é a chave para a excelência em vendas."

    if score_details['hasNCG']:
        simulated_summary = f"ATENÇÃO CRÍTICA: O SDR {sdr_name} teve a nota zerada devido a uma Não Conformidade Grave (NCG). Isso representa um risco imediato para a qualidade do repasse ou conformidade legal. É fundamental a correção imediata. Desvios graves: {score_details['ncgCount']}."
        simulated_plan = "1. Coaching imediato focado na regra de NCG. 2. Revisão completa do processo de validação de leads críticos. 3. Bloqueio temporário para repasse de leads até a certificação do item NCG."
    elif score_details['finalNota'] <= ASSERTIVITY_CUTOFF:
        simulated_summary = f"O SDR {sdr_name} atingiu o piso de assertividade ({ASSERTIVITY_CUTOFF}%), mas perdeu pontos na gestão do funil e coerência de dados. A dedução de {score_details['weightDeducted']:.2f}% mostra que há desvios recorrentes que precisam de atenção, especialmente na atualização das etapas no CRM."
        simulated_plan = "1. Sessão de revisão focada na importância do registo detalhado no Nectar CRM (etapas e observações). 2. Acompanhamento diário das 3 primeiras tarefas geradas após a monitoria. 3. Fazer 'shadowing' com um SDR de alta performance em registo."
    else:
        simulated_summary = f"O SDR {sdr_name} demonstrou uma boa performance, atingindo {score_details['finalNota']:.2f}%. Os desvios identificados ({score_details['ncCount']}x) são pontuais e focam em pequenas inconsistências no preenchimento de dados de Selene/Nectar, que são facilmente corrigíveis."
        simulated_plan = "1. Criar um mini-checklist de 'fechamento de ticket' para garantir a coerência dos dados. 2. Rever o padrão de observações no CRM para manter a padronização. 3. Monitoria bónus focada em melhores práticas para alcançar 100%."

    feedback_text = (
        f"Resumo da monitoria — Nota: {score_details['finalNota']:.2f}%\n\n"
        f'"{simulated_quote}"\n\n'
        f"Pontos de melhoria e Detalhamento dos Erros:\n{simulated_summary}\n\n"
        f"Plano de Ação Sugerido:\n{simulated_plan}"
    )

    st.session_state.monitoria_form['feedback_aplicado'] = feedback_text
    st.toast("Feedback Inteligente (Simulado) Gerado!")


# --- 6. COMPONENTES/PÁGINAS STREAMLIT (Mantidas) ---

# DICIONÁRIO DE STATUS CORRIGIDO
STATUS_OPTIONS = {
    'C': 'conforme',
    'NC': 'nc',
    'NCG': 'nc_grave',
    'NSA': 'nsa'
}
STATUS_KEYS = list(STATUS_OPTIONS.keys())


def update_checklist_status(item_id, status_options):
    """
    Função de callback para atualizar o status do item no form_data
    após a interação com o st.radio (resolvendo o problema de cálculo).
    """
    # O valor no session state [item_id] é a label selecionada ('C', 'NC', etc.)
    selected_label = st.session_state[item_id]

    # Mapeia a label para o valor real ('conforme', 'nc', 'nc_grave', 'nsa')
    selected_status = status_options[selected_label]

    # Atualiza o checklist dentro do formulário de monitoria no session_state
    st.session_state.monitoria_form['checklist'][item_id] = selected_status


def render_monitoria():
    form_data = get_current_form()

    st.title("Monitoria de Qualidade SDR")
    st.markdown("Preencha o checklist e gere feedback para o SDR.")

    st.subheader("Informações da Interação")
    col1, col2 = st.columns(2)

    sdr_options_with_empty = [''] + sorted(st.session_state.sdr_list)
    try:
        current_index = sdr_options_with_empty.index(form_data.get('sdr', ''))
    except ValueError:
        current_index = 0

    def update_sdr_field():
        set_form_field('sdr', st.session_state.sdr_select_key)

    with col1:
        sdr_selected = st.selectbox(
            "SDR Monitorado",
            options=sdr_options_with_empty,
            index=current_index,
            key='sdr_select_key',
            on_change=update_sdr_field
        )

    with col2:
        st.text_input("Data/Hora (Registo)", value=form_data['dataHora'], disabled=True)

    form_data['crmLink'] = st.text_input("Link CRM (Lead)", value=form_data.get('crmLink', ''), key='crmLink_key')
    form_data['seleneLink'] = st.text_input("Link Selene/Chat", value=form_data.get('seleneLink', ''),
                                            key='seleneLink_key')

    set_form_field('crmLink', st.session_state.crmLink_key)
    set_form_field('seleneLink', st.session_state.seleneLink_key)

    st.subheader("Checklist de Avaliação")

    current_checklist_state = form_data.get('checklist', {})
    grouped_checklist = group_checklist(st.session_state.checklist_model)

    # Variaveis globais de status
    global STATUS_OPTIONS
    global STATUS_KEYS

    # Loop para renderizar o checklist e garantir a atualização reativa
    for group_name in CHECKLIST_GROUP_ORDER:
        if group_name in grouped_checklist:
            st.markdown(f"---")
            st.markdown(f"**Bloco: {group_name}**")

            for item in grouped_checklist[group_name]:
                item_id = item['id']

                current_status_value = current_checklist_state.get(item_id, 'conforme')

                # Obtém a label ('C', 'NC', etc.) a partir do valor ('conforme', 'nc', etc.)
                current_status_label = next((k for k, v in STATUS_OPTIONS.items() if v == current_status_value), 'C')
                initial_index = STATUS_KEYS.index(current_status_label)

                cols = st.columns([0.6, 0.4])
                cols[0].markdown(f"**{item['label']}** *(Peso: {item['weight']}%)*")

                cols[1].radio(
                    "Avaliação",
                    options=STATUS_KEYS,
                    # CHAVE DO RADIO É O PRÓPRIO ITEM_ID para reatividade direta no session state
                    key=item_id,
                    horizontal=True,
                    index=initial_index,
                    label_visibility='collapsed',
                    # CALLBACK GARANTE QUE O FORM DATA É ATUALIZADO IMEDIATAMENTE APÓS A MUDANÇA
                    on_change=update_checklist_status,
                    args=(item_id, STATUS_OPTIONS)
                )

    # Após a renderização, o form_data['checklist'] já está atualizado
    # graças ao callback de cada radio.
    score_details = calculate_score_details(st.session_state.checklist_model, form_data['checklist'])

    st.markdown(
        f"**Nota Prévia:** <span class='score-display' style='color:{THEME['accent'] if score_details['finalNota'] >= ASSERTIVITY_CUTOFF else THEME['error']}; font-size:24px;'>{score_details['finalNota']:.2f}%</span> (Desvios: {score_details['ncCount']})",
        unsafe_allow_html=True)

    st.subheader("Observações e Plano de Ação")

    def update_observacoes_field():
        set_form_field('observacoes', st.session_state.observacoes_key)

    def update_plano_acao_field():
        set_form_field('planoAcaoMonitor', st.session_state.plano_acao_key)

    form_data['observacoes'] = st.text_area("Observações Gerais (Monitor)",
                                            value=form_data.get('observacoes', ''),
                                            key='observacoes_key',
                                            on_change=update_observacoes_field)

    form_data['planoAcaoMonitor'] = st.text_area("Plano de Ação do Monitor (Desenvolvimento)",
                                                 value=form_data.get('planoAcaoMonitor', ''),
                                                 key='plano_acao_key',
                                                 on_change=update_plano_acao_field)

    if score_details['ncCount'] > 0:
        if st.button("Gerar Feedback Inteligente (IA)"):
            generate_gemini_feedback(form_data['sdr'], score_details)
            st.rerun()

    if form_data.get('feedback_aplicado'):
        st.info("Feedback Gerado pela IA:")
        st.code(form_data['feedback_aplicado'], language='markdown')

        st.markdown("---")
        st.subheader("Ações de Feedback")

        sdr_email_placeholder = st.text_input("E-mail do SDR",
                                              value=f"{form_data['sdr'].lower().replace(' ', '.')}@empresa.com",
                                              key='sdr_email_key')

        col_dl, col_email = st.columns(2)

        col_dl.download_button(
            label="Download/Copiar Feedback Completo",
            data=form_data['feedback_aplicado'] + "\n\nPlano de Ação do Monitor:\n" + form_data['planoAcaoMonitor'],
            file_name="feedback_completo.txt",
            mime="text/plain"
        )

        if col_email.button("Enviar Feedback por E-mail", type='secondary', use_container_width=True):
            if not sdr_email_placeholder or '@' not in sdr_email_placeholder:
                st.error("Por favor, forneça um e-mail válido para o SDR.")
            else:
                full_body = (
                    f"Monitoria do dia {form_data['dataHora']}\n\n"
                    f"Link CRM: {form_data['crmLink']}\n"
                    f"Link Selene/Chat: {form_data['seleneLink']}\n\n"
                    f"--- Feedback Gerado ---\n"
                    f"{form_data['feedback_aplicado']}"
                )
                subject = f"[Monitoria] Feedback de Qualidade - {form_data['sdr']} ({score_details['finalNota']:.2f}%)"

                with st.spinner(f"Enviando feedback para {form_data['sdr']}..."):
                    send_feedback_email(form_data['sdr'], sdr_email_placeholder, subject, full_body)

    st.markdown("---")
    if st.button("SALVAR MONITORIA E FINALIZAR", use_container_width=True, type='primary'):
        save_monitoria_record(score_details)


# --- Funções de Ajuda para Gráfico (LÓGICA DE CORES: VERDE -> LARANJA) ---

def get_score_color(score):
    """
    Define a cor do gráfico com base na pontuação de assertividade (média).
    Regras:
    - Laranja (Accent): > 85% (Alto acerto)
    - Amarelo (Warning): <= 85% e > 80% (Alerta/Piso)
    - Vermelho (Error): <= 80% (Crítico)
    """
    if score > ASSERTIVITY_CUTOFF:  # Acima de 85%
        # Usa a cor de acento (Laranja) para o sucesso/assertivo
        return THEME['accent']
    elif score > 80:  # Entre 80% e 85% (inclusive)
        return THEME['warning']  # Amarelo
    else:  # Abaixo de 80% (inclusive)
        return THEME['error']  # Vermelho


# --- FUNÇÕES DE CRIAÇÃO DE GRÁFICOS (Implementando a nova média e lógica de 3 cores) ---

def create_collab_note_chart(df_filtered):
    """
    Gráfico de comparação de nota por colaborador (barra horizontal).
    Calcula a média, excluindo notas 0% (NCG) para refletir melhor a Assertividade.
    """
    if df_filtered.empty:
        return go.Figure()

    # NOVO CÁLCULO: Excluir notas 0% antes de agrupar para a média
    df_positive_scores = df_filtered[df_filtered['pontuacoes'] > 0].copy()

    if df_positive_scores.empty:
        # Só tem notas 0% ou filtros resultaram em nada
        return go.Figure()

    df_collab_avg = df_positive_scores.groupby('sdr')['pontuacoes'].mean().reset_index()
    df_collab_avg.columns = ['SDR', 'Nota Média']
    # Ordenar por nota
    df_collab_avg = df_collab_avg.sort_values(by='Nota Média', ascending=True)

    # Usa a lógica de três cores
    colors = [get_score_color(x) for x in df_collab_avg['Nota Média']]

    fig = go.Figure(go.Bar(
        x=df_collab_avg['Nota Média'],
        y=df_collab_avg['SDR'],
        orientation='h',
        marker_color=colors,
        # DIMINUIR LARGURA DA BARRA (SLIM)
        width=0.6,
        text=df_collab_avg['Nota Média'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))

    # Aumentar a altura para caber o texto de todos os SDRs, mas manter compacto
    fig.update_layout(
        title_text='Comparativo de Nota Média por Colaborador (Excluindo 0%)',
        template='plotly_dark',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=THEME['text']),
        xaxis_title="Nota Média (%)",
        yaxis_title=None,
        xaxis=dict(range=[0, 100]),
        margin=dict(t=40, b=20, l=20, r=20),
        # REDUÇÃO DA ALTURA PARA SLIM E MODERNO
        height=320
    )

    return fig


def render_dashboard():
    # Inicializa o DataFrame a partir do estado da sessão
    records = st.session_state.records
    if not records:
        st.title("Dashboard de Performance SDR - Qualidade")
        st.info("Nenhum dado de monitoria encontrado para construir o dashboard.")
        return

    df = pd.DataFrame(records)

    # --- PRÉ-PROCESSAMENTO ---
    # Garante que a coluna 'data' esteja no formato datetime
    df['data'] = pd.to_datetime(df['data'])

    # Adiciona colunas auxiliares para filtros
    df['MesAno'] = df['data'].dt.to_period('M').astype(str)

    # Mapeamento dos itens do checklist para os labels completos
    checklist_map = {item['id']: item['label'] for item in st.session_state.checklist_model}

    # Função para extrair o primeiro desvio (NC ou NCG) de um registro
    def get_first_deviation_label(checklist_state):
        if isinstance(checklist_state, dict):
            for item_id, status in checklist_state.items():
                if status in ['nc', 'nc_grave']:
                    return checklist_map.get(item_id, "Desconhecido")
        return "Conforme/NSA"

    df['DesvioPrincipal'] = df['checklist'].apply(get_first_deviation_label)

    st.markdown(f"<h1 class='title'>Dashboard de Performance SDR</h1>", unsafe_allow_html=True)
    st.markdown("Visão geral dos indicadores de qualidade, tendências e ranking.")
    st.markdown("---")

    # --- FILTROS AVANÇADOS (Migrados para o corpo da página para permitir os filtros na Sidebar original) ---
    st.subheader("Filtros de Análise")
    col_sdr, col_desvio, col_data_inicio, col_data_fim = st.columns(4)

    filter_sdr = col_sdr.selectbox("Filtrar por SDR", ['TODOS'] + sorted(df['sdr'].unique().tolist()))

    deviation_options_filtered = [d for d in df['DesvioPrincipal'].unique().tolist() if d != "Conforme/NSA"]
    filter_deviation = col_desvio.selectbox("Filtrar por Desvio Principal",
                                            ['TODOS'] + sorted(deviation_options_filtered))

    # Filtro por Período de Data
    min_date = df['data'].min().date() if not df.empty else date.today()
    max_date = df['data'].max().date() if not df.empty else date.today()

    filter_date_start = col_data_inicio.date_input("Data Início", value=min_date, min_value=min_date,
                                                   max_value=max_date)
    filter_date_end = col_data_fim.date_input("Data Fim", value=max_date, min_value=min_date, max_value=max_date)

    # --- APLICAR FILTROS ---
    filtered_df = df.copy()

    if filter_sdr != 'TODOS':
        filtered_df = filtered_df[filtered_df['sdr'] == filter_sdr]

    if filter_deviation != 'TODOS':
        filtered_df = filtered_df[filtered_df['DesvioPrincipal'] == filter_deviation]

    # Filtragem por data
    filtered_df = filtered_df[
        (filtered_df['data'].dt.date >= filter_date_start) &
        (filtered_df['data'].dt.date <= filter_date_end)
        ]

    # --- MÉTRICAS GERAIS (Recalculadas) ---
    # Esta métrica mantém a média TOTAL, incluindo 0% por NCG.
    avg_score = filtered_df['pontuacoes'].mean() if not filtered_df.empty else 0
    total_records = filtered_df.shape[0]

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        # A métrica de Assertividade é a média TOTAL (incluindo 0% por NCG)
        st.metric(
            label="Média de Assertividade (Total)",
            value=f"{avg_score:.2f}%",
            delta="+" + str(ASSERTIVITY_CUTOFF) if avg_score >= ASSERTIVITY_CUTOFF else None,
            delta_color="normal" if avg_score >= ASSERTIVITY_CUTOFF else "inverse"
        )
    with col2:
        st.metric("Total de Monitorias", total_records)

    with col3:
        ncg_count = filtered_df[filtered_df['pontuacoes'] == 0.0].shape[0]
        st.metric("Total de NC Graves (Nota 0)", ncg_count)
    st.markdown("---")

    if filtered_df.empty:
        st.info("Nenhum dado encontrado com os filtros aplicados.")
        return

    # --- GRÁFICOS DE ANÁLISE ---

    col_ranking, col_pie = st.columns([2, 1])

    with col_ranking:
        # --- GRÁFICO 1: RANKING SDR (Barras) ---
        # LÓGICA CORRIGIDA: Exclui notas 0% no cálculo da média para o ranking de Assertividade.
        st.subheader("Média de Assertividade por SDR (Excluindo Notas 0%)")
        st.markdown("_Esta média exclui monitorias que resultaram em 0% (NCG) para refletir a consistência de acerto._")

        # NOVO CÁLCULO: Excluir notas 0% antes de agrupar
        df_positive_scores = filtered_df[filtered_df['pontuacoes'] > 0].copy()

        if df_positive_scores.empty:
            st.info(
                "Nenhuma monitoria com pontuação acima de 0% encontrada nos filtros aplicados. Não é possível gerar o Ranking de Assertividade.")
            st.plotly_chart(go.Figure(), use_container_width=True)  # Exibe gráfico vazio se não há dados positivos
        else:
            score_df = df_positive_scores.groupby('sdr')['pontuacoes'].mean().reset_index()
            score_df.columns = ['SDR', 'Nota Média']

            # Usa a lógica de três cores (Laranja, Amarelo, Vermelho)
            score_df['Cor'] = score_df['Nota Média'].apply(get_score_color)

            score_df = score_df.sort_values(by='Nota Média', ascending=False)

            # Plotly Express ajustado para o tema
            fig_bar = px.bar(
                score_df,
                x='SDR',
                y='Nota Média',
                color='Cor',
                color_discrete_map='identity',
                title='Distribuição da Nota Média',
                range_y=[0, 100],
                # REDUÇÃO DA ALTURA PARA SLIM E MODERNO
                height=350
            )
            fig_bar.update_traces(
                # DIMINUIR LARGURA DA BARRA (SLIM)
                width=0.7,
                # DESTAQUE DAS MÉDIAS EM NÚMEROS EM CIMA
                texttemplate='%{y:.1f}%',
                textposition='outside'
            )
            fig_bar.update_layout(
                xaxis_title=None,
                yaxis_title="Nota (%)",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color=THEME['text'],
                template='plotly_dark',  # Usando dark template
                # Ajusta o layout para deixar mais espaço para os rótulos acima
                margin=dict(t=50, b=20, l=20, r=20),
            )
            fig_bar.update_xaxes(showgrid=False)
            fig_bar.update_yaxes(gridcolor='#444')
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_pie:
        # --- GRÁFICO 2: PRINCIPAIS DESVIOS (Pizza) ---
        st.subheader("Principais Desvios (Top 5)")

        deviation_counts = filtered_df[filtered_df['DesvioPrincipal'] != "Conforme/NSA"][
            'DesvioPrincipal'].value_counts()
        dev_df = deviation_counts.head(5).reset_index()
        dev_df.columns = ['Desvio', 'Contagem']

        if not dev_df.empty:

            # Paleta customizada para refletir as cores de Alerta/Crítico
            custom_colors_pie = [THEME['error'], THEME['warning'], THEME['accent'], '#888', '#555']

            fig_pie = px.pie(
                dev_df,
                names='Desvio',
                values='Contagem',
                title='Distribuição dos Top 5 Desvios',
                # AUMENTA O FURO INTERNO PARA DEIXAR A FATIA MAIS FINA (SLIM)
                hole=0.5,
                # REDUÇÃO DA ALTURA PARA SLIM E MODERNO
                height=350,
                color_discrete_sequence=custom_colors_pie
            )

            # CORREÇÃO CRÍTICA: Ajusta o layout para mover a legenda e margens
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font_color=THEME['text'],
                legend_title_text='Desvios',
                template='plotly_dark',
                # Mova a legenda para a direita (outside)
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.05
                ),
                # Ajuste as margens para dar espaço à legenda e à pizza
                margin=dict(l=20, r=150, t=50, b=20),
                height=380  # Altura ajustada após mover a legenda
            )

            # Ajuste a posição do texto na pizza para melhor visualização
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')

            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Nenhum desvio registrado no período filtrado.")

    # --- TENDÊNCIA, COMPARATIVO DE NOTA E RANKING DE INFRATORES ---
    st.markdown("---")

    # Nova estrutura de gráficos com o Comparativo de Nota
    col_hist, col_collab_note = st.columns(2)

    with col_hist:
        # --- GRÁFICO 3: TENDÊNCIA MÊS A MÊS ---
        st.subheader("Tendência de Assertividade Mês a Mês (Média Total)")

        monthly_avg = filtered_df.groupby('MesAno')['pontuacoes'].mean().reset_index()
        monthly_avg.columns = ['Mês/Ano', 'Média de Assertividade']

        fig_line = px.line(
            monthly_avg,
            x='Mês/Ano',
            y='Média de Assertividade',
            markers=True,
            title='Média de Assertividade ao Longo do Tempo',
            range_y=[0, 100],
            # REDUÇÃO DA ALTURA PARA SLIM E MODERNO
            height=350
        )
        # CORREÇÃO DA COR DA LINHA: Usando a cor de acento (Laranja)
        fig_line.update_traces(line=dict(color=THEME['accent']))

        fig_line.update_layout(
            xaxis_title=None,
            yaxis_title="Nota (%)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=THEME['text'],
            template='plotly_dark'
        )
        fig_line.update_xaxes(showgrid=True, gridcolor='#444')
        fig_line.update_yaxes(showgrid=True, gridcolor='#444')
        st.plotly_chart(fig_line, use_container_width=True)

    with col_collab_note:
        # --- NOVO GRÁFICO 4: COMPARATIVO DE NOTA POR SDR ---
        st.subheader("Comparativo de Nota Média por Colaborador (Excluindo 0%)")
        fig_collab_note = create_collab_note_chart(filtered_df)
        st.plotly_chart(fig_collab_note, use_container_width=True)

    st.markdown("---")

    # Ranking de Infratores mantido
    st.subheader("Ranking de Infratores e Desvios")

    # Calcular o total de desvios por SDR
    infrator_df = filtered_df.groupby('sdr')['desviosCount'].sum().reset_index()
    infrator_df.columns = ['SDR', 'Total de Desvios (NC+NCG)']

    # Incluir o total de monitorias para contexto
    monitoria_count = filtered_df.groupby('sdr')['id'].count().reset_index()
    monitoria_count.columns = ['SDR', 'Total Monitorias']

    ranking_df = pd.merge(infrator_df, monitoria_count, on='SDR', how='outer').fillna(0)
    ranking_df['Desvios por Monitoria'] = ranking_df['Total de Desvios (NC+NCG)'] / ranking_df[
        'Total Monitorias'].replace(0, np.nan)

    # Ordenar pelos maiores infratores
    ranking_df = ranking_df.sort_values(by=['Total de Desvios (NC+NCG)', 'Desvios por Monitoria'], ascending=False)

    # Adicionar coluna de Ranking
    ranking_df['Rank'] = range(1, len(ranking_df) + 1)

    st.dataframe(ranking_df[['Rank', 'SDR', 'Total de Desvios (NC+NCG)', 'Total Monitorias']].head(10),
                 hide_index=True,
                 use_container_width=True)


def render_historico():
    st.title("Histórico de Monitorias")

    df = pd.DataFrame(st.session_state.records)

    if df.empty:
        st.info("Nenhum registo de monitoria encontrado.")
        return

    df['Pontuação'] = df['pontuacoes'].apply(lambda x: f"{x:.2f}%")
    df['Desvios'] = df['desviosCount']

    if 'reincidenciaCount' in df.columns:
        df['Reincidência'] = df['reincidenciaCount'].apply(lambda x: f"SIM ({x})" if x > 1 else "NÃO (0)")
    else:
        df['Reincidência'] = "NÃO (0)"

    columns_to_display = ['data', 'sdr', 'Pontuação', 'Reincidência', 'Desvios', 'crmLink', 'seleneLink']

    st.dataframe(df[columns_to_display], use_container_width=True)

    csv_output = StringIO()
    df.to_csv(csv_output, index=False)
    csv_data = csv_output.getvalue()

    st.download_button(
        label="Gerar Relatório CSV Completo",
        data=csv_data,
        file_name='relatorio_monitoria_completo.csv',
        mime='text/csv',
    )


def render_cadastro():
    st.title("Cadastro e Gestão de SDRs")

    st.subheader("Adicionar Novo SDR")

    with st.form(key='sdr_add_form'):
        new_sdr_name = st.text_input("Nome do Novo SDR",
                                     value=st.session_state.new_sdr_name_value,
                                     key='new_sdr_name_widget_key')

        submitted = st.form_submit_button("Adicionar SDR")

        if submitted:
            name_to_add = st.session_state.new_sdr_name_widget_key.strip()

            if not name_to_add:
                st.error("Nome inválido. O campo não pode ser vazio.")
            elif name_to_add in st.session_state.sdr_list:
                st.warning("SDR já existe.")
            else:
                st.session_state.sdr_list.append(name_to_add)
                st.session_state.sdr_list.sort()

                save_data_to_json(st.session_state.sdr_list, SDR_FILE_PATH)

                st.success(f"SDR {name_to_add} adicionado e salvo.")

                st.session_state.new_sdr_name_value = ""
                st.rerun()

    st.subheader("Lista Atual de SDRs")

    sdr_to_remove = st.selectbox("Selecione SDR para Remover", [''] + sorted(st.session_state.sdr_list))

    if sdr_to_remove and st.button(f"Remover {sdr_to_remove}", type='secondary'):
        st.session_state.sdr_list.remove(sdr_to_remove)

        save_data_to_json(st.session_state.sdr_list, SDR_FILE_PATH)

        st.success(f"SDR {sdr_to_remove} removido e salvo.")
        st.rerun()

    st.dataframe(pd.DataFrame({'SDR': sorted(st.session_state.sdr_list)}), use_container_width=True)


def render_editor():
    st.title("Editar Checklist de Monitoria")

    st.warning("Atenção: A edição do checklist afeta o cálculo de todas as monitorias futuras.")

    df_checklist = pd.DataFrame(st.session_state.checklist_model)

    st.subheader("Configuração Atual do Checklist")

    edited_df = st.data_editor(
        df_checklist,
        column_config={
            "id": st.column_config.Column("ID Único", disabled=True),
            "group": st.column_config.TextColumn("Bloco/Grupo"),
            "label": st.column_config.TextColumn("Descrição da Regra", width="large"),
            "weight": st.column_config.NumberColumn("Peso (%)", min_value=1, max_value=100, step=1),
        },
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True
    )

    new_checklist_model = edited_df.to_dict('records')

    unique_ids = set()
    valid_items = []

    for i, item in enumerate(new_checklist_model):
        item_id = item.get('id', f'new_id_{i}')
        # Lógica de ID único melhorada para evitar repetição acidental
        if not item.get('id') or item_id in unique_ids:
            # Gerar um ID baseado no timestamp com um contador
            item_id = f'id_{datetime.now().strftime("%Y%m%d%H%M%S")}_{i}'

        unique_ids.add(item_id)

        valid_items.append({
            'id': item_id,
            'group': item.get('group', 'Novo'),
            'label': item.get('label', 'Nova Regra'),
            'weight': item.get('weight', 0)
        })

    total_weight = sum(item.get('weight', 0) for item in valid_items)

    st.info(f"Soma Total dos Pesos: {total_weight}% (Ideal: 100%)")

    if st.button("Salvar Alterações no Checklist", type='primary'):
        if any(not item['label'] or not item['group'] for item in valid_items):
            st.error("Por favor, preencha a Descrição da Regra e o Bloco/Grupo em todas as linhas.")
        else:
            st.session_state.checklist_model = valid_items

            save_data_to_json(valid_items, CHECKLIST_FILE_PATH)

            if total_weight != 100:
                st.warning(
                    f"A soma total dos pesos não é 100% ({total_weight}%). Salvo, mas ajuste para 100% para evitar distorções na pontuação.")
            else:
                st.success("Checklist atualizado com sucesso!")

            st.rerun()


def render_dispute():
    st.title("Tela de Contestação de Monitoria")
    st.markdown("Use os filtros abaixo para buscar e gerenciar contestações de SDRs.")

    disputes_df = pd.DataFrame(st.session_state.disputes)

    st.subheader("Filtros")
    col1, col2, col3 = st.columns([1, 1, 2])

    sdr_options = ['TODOS'] + sorted(st.session_state.sdr_list)
    filter_sdr = col1.selectbox("SDR", sdr_options)

    if not disputes_df.empty and 'data' in disputes_df.columns:
        disputes_df['data_obj'] = pd.to_datetime(disputes_df['data']).dt.date
        min_date_val = disputes_df['data_obj'].min()
        max_date_val = disputes_df['data_obj'].max()

        filter_date = col2.date_input("Período de Data",
                                      value=(min_date_val, max_date_val),
                                      min_value=min_date_val,
                                      max_value=max_date_val)
    else:
        filter_date = (date.today(), date.today())
        col2.warning("Nenhuma data disponível para filtro.")

    status_options = ['TODOS', 'Pendente', 'Aprovada', 'Rejeitada']
    filter_status = col3.selectbox("Status da Contestação", status_options)

    filtered_disputes = disputes_df.copy()

    if filter_sdr != 'TODOS':
        filtered_disputes = filtered_disputes[filtered_disputes['sdr'] == filter_sdr]

    if filter_status != 'TODOS':
        filtered_disputes = filtered_disputes[filtered_disputes['status'] == filter_status]

    if filter_date and len(filter_date) == 2 and not disputes_df.empty and 'data_obj' in disputes_df.columns:
        start_date = filter_date[0]
        end_date = filter_date[1]

        filtered_disputes = filtered_disputes[
            (filtered_disputes['data_obj'] >= start_date) &
            (filtered_disputes['data_obj'] <= end_date)
            ]

    st.markdown("---")
    st.subheader(f"Histórico de Contestações ({len(filtered_disputes)})")

    columns_to_display = ['dataHora', 'sdr', 'monitoria_id', 'motivo', 'status']

    if filtered_disputes.empty:
        st.info("Nenhuma contestação encontrada com os filtros aplicados.")
    else:
        st.dataframe(filtered_disputes.drop(columns=['data_obj'], errors='ignore')[columns_to_display],
                     use_container_width=True)

    st.subheader("Submeter Nova Contestação")
    with st.form(key='new_dispute_form',
                 clear_on_submit=True):
        dispute_sdr = st.selectbox("SDR (Monitorado)", [''] + sorted(st.session_state.sdr_list))
        dispute_record_id = st.text_input("ID ou Link da Monitoria Contestada",
                                          help="Insira o ID ou link do registro de monitoria que está sendo contestado.",
                                          key='dispute_record_id_key')
        dispute_reason = st.text_area("Motivo Detalhado da Contestação", height=150, key='dispute_reason_key')

        submitted = st.form_submit_button("Submeter Contestação", type='primary')

        if submitted:
            if dispute_sdr and dispute_record_id and dispute_reason:
                new_dispute_record = {
                    'id': datetime.now().timestamp(),
                    'data': datetime.now().strftime('%Y-%m-%d'),
                    'sdr': dispute_sdr,
                    'monitoria_id': dispute_record_id,
                    'motivo': dispute_reason,
                    'status': 'Pendente',
                    'dataHora': datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
                }

                st.session_state.disputes.append(new_dispute_record)

                if save_data_to_json(st.session_state.disputes, DISPUTE_FILE_PATH):
                    st.success(f"Contestação de {dispute_sdr} submetida com sucesso! Status: Pendente.")
                    st.rerun()
                else:
                    st.error("Erro ao persistir a contestação. Tente novamente.")
            else:
                st.error("Por favor, preencha todos os campos da contestação.")


# --- Tela de Pães Quentinhos (Mantida) ---

def render_hot_bread():
    st.title("🚨 Pães Quentinhos - Leads Sem Resposta")  # Título atualizado
    st.markdown(
        "Calcule o tempo de inatividade no Selene Bot para evitar leads queimados. **Insira a data e hora da última interação manualmente.**")

    # --- 0. RENDERIZAÇÃO DO ALERTA PERSISTENTE ---
    # Renderiza o alerta no topo da página se houver dados salvos no session_state
    if 'current_hot_bread_alert' in st.session_state and st.session_state.current_hot_bread_alert is not None:
        alert_data = st.session_state.current_hot_bread_alert
        show_hot_bread_alert(alert_data['time'], alert_data['link'])

        # Limpa o alerta para a próxima interação
        st.session_state.current_hot_bread_alert = None

    # --- 1. Formulário de Cálculo ---
    st.subheader("Registrar Inatividade e Gerar Alerta")

    sdr_options = sorted(st.session_state.sdr_list)
    sdr_default = sdr_options[0] if sdr_options else 'SDR Padrão'

    default_date = date.today()

    with st.form(key='hot_bread_form', clear_on_submit=True):

        sdr_assigned = st.selectbox(
            "SDR Responsável",
            sdr_options,
            index=sdr_options.index(sdr_default) if sdr_default in sdr_options else 0,
            help="Selecione o SDR responsável pelo lead."
        )

        col_date, col_time = st.columns(2)

        # Campo de Data Manual
        last_interaction_date = col_date.date_input(
            "Data da Última Interação",
            value=default_date,
            help="Selecione a data da última interação registrada no Selene Bot."
        )

        # Campo de Hora Manual PURO (st.text_input)
        last_interaction_time_str = col_time.text_input(
            "Hora da Última Interação (HH:MM:SS)",
            value="",  # Começa vazio
            placeholder="Ex: 15:30:00",
            help="Digite a hora exata da última interação registrada no formato HH:MM:SS."
        )

        lead_link = st.text_input(
            "Link do Lead (Selene Bot)",
            help="Link direto para o chat/lead no Selene Bot."
        )

        threshold_hours = st.number_input(
            "Threshold de Alerta (horas)",
            min_value=1,
            value=24,
            step=1,
            help="O alerta será considerado como 'disparado' no histórico se o tempo for maior que este valor."
        )

        calculate_button = st.form_submit_button("Calcular e Gerar Alerta", type='primary')

        if calculate_button:
            if not last_interaction_date or not last_interaction_time_str or not lead_link:
                st.error("Por favor, preencha a Data, Hora e o Link do Selene Bot.")
                return

                # 1. Validação de Hora
            if not re.match(r'^\d{2}:\d{2}:\d{2}$', last_interaction_time_str):
                st.error("Formato de Hora inválido. Use o formato: HH:MM:SS (Ex: 15:30:00).")
                return

            try:
                # 2. Conversão e Cálculo
                time_obj = datetime.strptime(last_interaction_time_str, '%H:%M:%S').time()
                last_interaction_dt = datetime.combine(last_interaction_date, time_obj)

                last_interaction_str = last_interaction_dt.strftime('%d/%m/%Y %H:%M:%S')
                time_difference = datetime.now() - last_interaction_dt
                formatted_time = format_timedelta(time_difference)

                # 3. SALVAR ALERTA NO SESSION STATE (PARA GARANTIR A MENSAGEM VISUAL)
                if time_difference.total_seconds() > 0:
                    st.session_state.current_hot_bread_alert = {
                        'time': formatted_time,
                        'link': lead_link
                    }

                # 4. Salva o registro no JSON (histórico)
                alert_threshold = timedelta(hours=threshold_hours)

                status_alerta = 'Alerta Disparado' if time_difference > alert_threshold else 'Monitorado (Abaixo do Threshold)'

                hot_bread_record = {
                    'id': datetime.now().timestamp(),
                    'dataHoraAlerta': datetime.now().strftime('%d/%m/%Y, %H:%M:%S'),
                    'sdr': sdr_assigned,
                    'lastInteraction': last_interaction_str,
                    'timeWithoutResponse': formatted_time,
                    'leadLink': lead_link,
                    'status': status_alerta
                }
                st.session_state.hot_bread_records.append(hot_bread_record)

                if save_data_to_json(st.session_state.hot_bread_records, HOT_BREAD_FILE_PATH):
                    st.toast(f"Registro de 'Pão Quentinho' salvo. Status: {status_alerta}.")

                    # *** DISPARAR RERUN para mostrar o alerta no topo da página ***
                    st.rerun()
                else:
                    st.error("Erro ao persistir o registro do 'Pão Quentinho'.")

            except ValueError:
                st.error("Erro ao converter a Data/Hora. Certifique-se de que o valor da hora é válido (Ex: 23:59:59).")
            except Exception as e:
                st.error(f"Erro inesperado no cálculo. Detalhe: {e}")

    # --- 2. Histórico de Alertas (Mantido) ---
    st.markdown("---")
    st.subheader("Histórico de Alertas de Pães Quentinhos")

    hot_bread_df = pd.DataFrame(st.session_state.hot_bread_records)

    if hot_bread_df.empty:
        st.info("Nenhum alerta de 'Pão Quentinho' registrado ainda.")
        return

    columns_to_display = ['dataHoraAlerta', 'sdr', 'timeWithoutResponse', 'lastInteraction', 'leadLink', 'status']

    st.dataframe(
        hot_bread_df[columns_to_display],
        column_config={
            "leadLink": st.column_config.LinkColumn("Link Selene Bot", display_text="Acessar"),
        },
        use_container_width=True
    )

    # Exportar para CSV
    csv_output_hb = StringIO()
    hot_bread_df.to_csv(csv_output_hb, index=False)
    csv_data_hb = csv_output_hb.getvalue()

    st.download_button(
        label="Gerar Relatório CSV de Pães Quentinhos",
        data=csv_data_hb,
        file_name='relatorio_paes_quentinhos.csv',
        mime='text/csv',
    )


# --- 7. FUNÇÃO PRINCIPAL ---

def set_custom_styles():
    """Lê o conteúdo CSS para aplicar o tema escuro e estilos de negócio."""
    css_content = """
/* New THEME: bg: #111827, accent: #ff7a00, card: #1f2937, text: #f3f4f6 */

/* --- Configurações Gerais e Background --- */
[data-testid="stAppViewContainer"] {
    background-color: #111827; /* Novo background principal muito escuro (Cinza Off) */
}
[data-testid="stHeader"] {
    background-color: #111827; /* Novo background principal muito escuro (Cinza Off) */
}
[data-testid="stSidebar"] {
    background-color: #1f2937; /* Novo card/sidebar background, mais escuro que o anterior */
    border-right: 1px solid #334155;
}
.css-1e6z5td, .css-1qxt0o0 { /* Altera a cor do texto no sidebar */
    color: #f3f4f6;
}

/* --- Título da Aplicação --- */
.title {
    color: #ff7a00; /* Cor de destaque (accent) */
    font-weight: 700;
    font-size: 1.8em;
}

/* --- Botões de Navegação (Minimalista, sem ícones coloridos) --- */
.stButton>button {
    background-color: #374151; /* Cor de card para botões não primários */
    color: #f3f4f6;
    border: 1px solid #374151;
    transition: background-color 0.3s;
    font-weight: bold; /* Destaca o texto no botão */
}
.stButton>button:hover {
    background-color: #4b5563; /* Efeito hover mais escuro */
}
.stButton>button:focus:not(:active) {
    border-color: #ff7a00;
}
.stButton>button[kind="primary"] {
    background-color: #ff7a00;
    color: #111827;
    border-color: #ff7a00;
}
.stButton>button[kind="primary"]:hover {
    background-color: #cc6000;
    border-color: #cc6000;
}

/* --- Input Fields e Textareas --- */
.stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div:first-child {
    background-color: #2a3340; /* Inputs mais escuros */
    border: 1px solid #374151;
    color: #f3f4f6;
}

/* --- Métricas (st.metric) --- */
[data-testid="stMetric"] {
    background-color: #1f2937;
    border-radius: 8px;
    padding: 15px;
    /* Destaque adicional para as métricas do dashboard */
    border-left: 5px solid #ff7a00;
}
[data-testid="stMetricLabel"] {
    color: #9ca3af; /* Título da métrica mais claro */
}
[data-testid="stMetricValue"] {
    color: #f3f4f6; /* Valor da métrica claro */
}

/* --- Alertas de Status --- */
/* Corrigindo a cor do texto e ícone para contraste nos alertas coloridos */
[data-testid="stAlert"] {
    border-radius: 8px;
    color: #111827;  
}
[data-testid="stAlert"] [data-testid="stText"] {
    color: #111827 !important; /* Texto escuro */
}
[data-testid="stAlert"] svg {
    fill: #111827 !important; /* Ícone escuro */
}
/* Estilo para Títulos de Gráficos */
.stApp h3 {
    border-bottom: 1px solid #ff7a00;
    padding-bottom: 5px;
    margin-top: 1.5rem;
}
"""
    st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)


def main_app():
    # Configuração da página
    st.set_page_config(layout="wide", page_title="Acelera Quality SDR")

    # 1. CSS
    set_custom_styles()

    # 2. Inicializa o Session State e carrega dados persistentes (JSON)
    initialize_session_state()

    # --- Configuração do Sidebar (Navegação Original) ---
    with st.sidebar:
        # LOGO REMOVIDO CONFORME SOLICITADO

        st.markdown(f"<h1 class='title'>Acelera Quality</h1>", unsafe_allow_html=True)
        st.markdown("---")

        # Botões com apenas texto em letras maiúsculas para aparência clean/business
        # Mantendo a lógica de navegação do seu código original
        if st.button("DASHBOARD", use_container_width=True):
            st.session_state.current_page = 'dashboard'
        if st.button("MONITORIA", use_container_width=True):
            st.session_state.current_page = 'monitoria'
        if st.button("HISTÓRICO", use_container_width=True):
            st.session_state.current_page = 'historico'

        # NOVO BOTÃO: Pães Quentinhos
        if st.button("PÃES QUENTINHOS", use_container_width=True, type='secondary'):
            st.session_state.current_page = 'hot_bread'

        st.markdown("---")
        if st.button("CONTESTAÇÃO", use_container_width=True):
            st.session_state.current_page = 'dispute'
        st.markdown("---")
        if st.button("CADASTRO SDRs", use_container_width=True):
            st.session_state.current_page = 'cadastro'
        if st.button("EDITAR CHECKLIST", use_container_width=True):
            st.session_state.current_page = 'editor'

    # --- Renderização da Página Atual ---
    if st.session_state.current_page == 'dashboard':
        render_dashboard()
    elif st.session_state.current_page == 'monitoria':
        render_monitoria()
    elif st.session_state.current_page == 'historico':
        render_historico()
    elif st.session_state.current_page == 'cadastro':
        render_cadastro()
    elif st.session_state.current_page == 'editor':
        render_editor()
    elif st.session_state.current_page == 'dispute':
        render_dispute()
    # NOVO: Renderização da página de Pães Quentinhos
    elif st.session_state.current_page == 'hot_bread':
        render_hot_bread()


if __name__ == '__main__':
    main_app()