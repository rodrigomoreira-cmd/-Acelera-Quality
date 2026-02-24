import calendar
from datetime import datetime
import pytz

def verificar_janela_aberta():
    """
    Retorna True se estivermos nos primeiros 3 dias do mês 
    ou nos últimos 3 dias do mês atual.
    """
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date()
    dia_atual = hoje.day
    
    # Descobre qual é o último dia do mês atual
    _, ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)
    
    # Define o dia em que a janela abre no final do mês
    dia_abertura_fim_mes = ultimo_dia_mes - 3
    
    if dia_atual <= 3:
        return True, "Janela de fechamento aberta (Mês anterior)."
    elif dia_atual >= dia_abertura_fim_mes:
        return True, "Janela de fechamento aberta (Mês atual)."
    else:
        dias_faltantes = dia_abertura_fim_mes - dia_atual
        return False, f"⚠️ Período bloqueado. A próxima janela de contestação abre daqui a {dias_faltantes} dia(s)."