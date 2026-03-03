import streamlit as st
from groq import Groq

# Inicializa o cliente Groq
try:
    CHAVE_GROQ = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=CHAVE_GROQ)
except Exception:
    st.error("⚠️ Chave GROQ_API_KEY não encontrada nos secrets.")

# ---------------------------------------------------------
# 1. FUNÇÃO PARA CONTESTAÇÕES (SENTIMENTO)
# ---------------------------------------------------------
def analisar_sentimento_texto(texto):
    if not texto or len(texto.strip()) < 5:
        return "🟡 Neutro", "Texto muito curto para análise."

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um especialista em RH. Analise o sentimento desta contestação.\n"
                        "Responda exatamente no formato:\n"
                        "Sentimento: [🟢 Positivo, 🟡 Neutro ou 🔴 Negativo]\n"
                        "Resumo: [Motivo em 1 linha]"
                    )
                },
                {
                    "role": "user",
                    "content": texto,
                }
            ],
            model="llama-3.1-8b-instant", 
            temperature=0.2, 
        )

        res_ia = chat_completion.choices[0].message.content
        
        sentimento = "🟡 Neutro"
        resumo = "Resumo indisponível."
        
        for linha in res_ia.split('\n'):
            if "Sentimento:" in linha:
                sentimento = linha.split("Sentimento:")[1].strip()
            elif "Resumo:" in linha:
                resumo = linha.split("Resumo:")[1].strip()
        
        return sentimento, resumo

    except Exception as e:
        return "⚪ Erro", f"Falha no Groq: {str(e)}"


# ---------------------------------------------------------
# 2. FUNÇÃO PARA MONITORIAS (SUGESTÃO DE PDI/FEEDBACK)
# ---------------------------------------------------------
def sugerir_pdi_ia(itens_reprovados, departamento):
    """
    Gera um PDI (Plano de Desenvolvimento Individual) curto baseado nos erros.
    """
    if not itens_reprovados:
        return "Excelente atendimento! Você seguiu todos os processos com perfeição."

    # Monta a lista de erros para o prompt
    texto_erros = "\n".join([f"- Item: {k} | Motivo: {v}" for k, v in itens_reprovados.items()])
    
    prompt = f"""
    Você é um mentor de vendas e qualidade para o setor de {departamento}.
    O colaborador cometeu os seguintes erros na monitoria:
    {texto_erros}
    
    Escreva um feedback direto para o colaborador. 
    1. Comece com um ponto positivo geral.
    2. Explique brevemente como corrigir os itens reprovados.
    3. Seja motivador, mas profissional.
    Máximo 5 linhas. Responda apenas com o texto do feedback, sem introduções.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.6,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Erro ao gerar sugestão da IA: {str(e)}"
    
# ---------------------------------------------------------
# 3. FUNÇÃO PARA AVALIAÇÃO DE LIDERANÇA (TERMÔMETRO)
# ---------------------------------------------------------
def analisar_clima_lideranca(texto):
    """
    Analisa comentários sobre líderes e classifica o clima organizacional.
    """
    if not texto or len(texto.strip()) < 5:
        return "⚪ Sem dados", "Comentário muito curto para análise."

    prompt = f"""
    Você é um especialista em RH e Clima Organizacional. Analise este feedback de um liderado sobre seu gestor.
    
    Feedback: "{texto}"
    
    Classifique o clima/tom da mensagem e faça um resumo.
    Responda EXATAMENTE neste formato:
    Sentimento: [🟢 Elogio, 🟡 Construtivo ou 🔴 Alerta Crítico]
    Resumo: [Motivo principal em até 10 palavras]
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.1, # Temperatura baixa para análises mais precisas e padronizadas
        )
        res_ia = chat_completion.choices[0].message.content
        
        sentimento = "🟡 Construtivo"
        resumo = "Resumo indisponível."
        
        for linha in res_ia.split('\n'):
            if "Sentimento:" in linha:
                sentimento = linha.split("Sentimento:")[1].strip()
            elif "Resumo:" in linha:
                resumo = linha.split("Resumo:")[1].strip()
        
        return sentimento, resumo

    except Exception as e:
        return "⚪ Erro", f"Falha na IA: {str(e)}"