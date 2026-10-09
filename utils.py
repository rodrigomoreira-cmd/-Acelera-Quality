import calendar
from datetime import datetime
import pytz
from typing import Tuple

def verificar_janela_aberta() -> Tuple[bool, str]:
    """
    Retorna True se estivermos nos primeiros 3 dias do mês 
    ou nos últimos 3 dias do mês atual.
    """
    try:
        fuso = pytz.timezone('America/Sao_Paulo')
        hoje = datetime.now(fuso).date()
        dia_atual = hoje.day
        
        # Descobre qual é o último dia do mês atual
        _, ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)
        
        # Define o dia em que a janela abre no final do mês (Últimos 3 dias)
        # Ex: Mês de 31 dias -> 31 - 2 = 29. A janela abre nos dias 29, 30 e 31.
        dia_abertura_fim_mes = ultimo_dia_mes - 2
        
        if dia_atual <= 3:
            return True, "Janela de fechamento aberta (Mês anterior)."
        elif dia_atual >= dia_abertura_fim_mes:
            return True, "Janela de fechamento aberta (Mês atual)."
        else:
            dias_faltantes = dia_abertura_fim_mes - dia_atual
            return False, f"⚠️ Período bloqueado. A próxima janela de avaliação/contestação abre daqui a {dias_faltantes} dia(s)."
            
    except Exception as e:
        # Falha de segurança: Em caso de erro de servidor/fuso, libera o acesso para não travar a operação
        print(f"Erro na verificação de data: {e}")
        return True, "Janela de fechamento aberta (Modo de Segurança)."