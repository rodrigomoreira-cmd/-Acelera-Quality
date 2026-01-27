# engine.py

# 1. CONSTANTES E TEMA
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

# 2. MODELO DO CHECKLIST (Coloque sua lista aqui)
CHECKLIST_MODEL = [
    {"id": "atualizacao_crm", "group": "Nectar CRM", "label": "As etapas do funil estão atualizadas e com histórico descritivo completo e coerente?", "weight": 5},
    {"id": "classificacao_funil", "group": "Nectar CRM", "label": "O SDR seguiu todas as etapas obrigatórias (conexão, pré-qualificação, registo, follow-up)?", "weight": 4},
    {"id": "etapa_pre_qual", "group": "Nectar CRM", "label": "Foram coletadas e registadas as informações iniciais sobre perfil, interesse e fit?", "weight": 4},
    {"id": "etapa_agendamento", "group": "Nectar CRM", "label": "A reunião foi agendada dentro do padrão (datas próximas e validação pelo gestor)?", "weight": 4},
    {"id": "validacao_sla", "group": "Nectar CRM", "label": "O SLA de tempo de resposta e registo de follow-up foi cumprido conforme política interna?", "weight": 2},
    {"id": "autorizacao_agendamento", "group": "Nectar CRM", "label": "O lead fora do ICP foi agendado sem validação prévia da gestão? (NC se sim)", "weight": 5},
    {"id": "campos_obrigatorios", "group": "Nectar CRM", "label": "Todos os campos obrigatórios (tarefas e formulário) estão preenchidos corretamente?", "weight": 4},
    {"id": "descarte_lead", "group": "Nectar CRM", "label": "O lead encerrado foi classificado corretamente (motivo e status final compatíveis)?", "weight": 4},
    {"id": "obs_padronizadas", "group": "Nectar CRM", "label": "As observações no CRM seguem o padrão de descrição definido pela área de qualidade?", "weight": 4},
    {"id": "retorno_reabertos", "group": "Nectar CRM", "label": "Caso o lead tenha sido reaberto, o histórico e motivo estão claramente justificados?", "weight": 4},
    {"id": "etapa_conexao", "group": "Ambos - Processo SDR", "label": "O SDR estabeleceu contacto efetivo (mensagem ou ligação)? Houve resposta do lead?", "weight": 4},
    {"id": "etapa_qualificacao", "group": "Ambos - Processo SDR", "label": "Foi validado se o lead se encaixa no ICP? As respostas foram registadas no CRM?", "weight": 4},
    {"id": "consistencia_comunicacao", "group": "Ambos - Processo SDR", "label": "A linguagem e abordagem utilizadas estão de acordo com o padrão de comunicação da marca?", "weight": 4},
    {"id": "followup_reg", "group": "Identificar - Processo", "label": "Foi realizado follow-up dentro do prazo padrão (até 24h após contacto)? (NC se ausente)", "weight": 5},
    {"id": "lead_parado", "group": "Identificar - Processo", "label": "O lead está parado no CRM há mais de 5 dias? - Descartar - (NC se sim)", "weight": 5},
    {"id": "transicao_sistemas", "group": "Integração", "label": "O lead foi transferido corretamente, sem duplicidade, perda ou erro de status?", "weight": 2},
    {"id": "tempo_atendimento", "group": "Selene/Bot", "label": "O lead foi atendido dentro de 15 minutos no Selenebot? (NC se não atendido)", "weight": 8},
    {"id": "inicio_selenebot", "group": "Selene/Bot", "label": "A primeira interação ocorreu dentro do Selenebot, conforme o fluxo definido?", "weight": 8},
    {"id": "coerencia_dados", "group": "Selene/Bot", "label": "As informações do lead (nome, telefone, status, ICP) estão idênticas entre Selene e Nectar?", "weight": 6},
    {"id": "inicio_selene", "group": "Selene/Bot", "label": "O atendimento foi iniciado no Selene com mensagem inicial e encerramento formal do ticket?", "weight": 4},
]

# 3. FUNÇÃO DE CÁLCULO
def calculate_score_details(checklist_model, checklist_state):
    """
    Calcula a nota final da monitoria com base no checklist e status.
    Regra: Subtrai o peso de cada NC e zera a nota se houver NC Grave.
    """
    total_score = 100.0
    weight_deducted = 0
    nc_count = 0
    ncg_count = 0
    nc_items = []
    has_ncg = False

    for item in checklist_model:
        val = checklist_state.get(item["id"])
        weight = item["weight"] or 0

        if val is None or val == 'nsa':
            continue

        if val == 'nc' or val == 'nc_grave':
            nc_count += 1
            nc_items.append(item)
            weight_deducted += weight
            total_score -= weight

            if val == 'nc_grave':
                ncg_count += 1
                has_ncg = True

    if total_score < 0:
        total_score = 0.0

    final_nota = total_score
    if has_ncg:
        final_nota = 0.0

    return {
        "finalNota": final_nota,
        "weightDeducted": weight_deducted,
        "ncCount": nc_count,
        "ncgCount": ncg_count,
        "ncItems": nc_items,
        "hasNCG": has_ncg,
    }