import streamlit as st
import pandas as pd
import time
import uuid
from database import salvar_monitoria_auditada, supabase

# --- IMPORT DA IA AQUI ---
from analise_ia import sugerir_pdi_ia
# -------------------------

def render_nova_monitoria():
    dept_selecionado = st.session_state.get('departamento_selecionado', 'Todos')
    nivel_logado = st.session_state.get('nivel', 'USUARIO').upper()
    
    st.title("📝 Nova Monitoria")
    st.markdown("Preencha o checklist. Itens marcados com 🚩 são **Fatais** e zeram a nota em caso de erro.")
    
    # ==========================================================
    # 1. BUSCA DE CRITÉRIOS E USUÁRIOS
    # ==========================================================
    try:
        res_crit = supabase.table("criterios_qa").select("*").eq("esta_ativo", True).execute()
        df_criterios = pd.DataFrame(res_crit.data) if res_crit.data else pd.DataFrame()
        
        res_users = supabase.table("usuarios").select("nome, email, departamento, nivel").eq("esta_ativo", True).execute()
        df_users = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return

    # 🛡️ TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
    if not df_users.empty:
        df_users = df_users[
            (~df_users['email'].astype(str).str.contains('admin@grupoacelerador.com.br', na=False, case=False)) &
            (~df_users['nome'].astype(str).str.contains('admin@grupoacelerador.com.br', na=False, case=False))
        ].copy()

    # Filtro de Colaboradores baseado no Menu Lateral
    if not df_users.empty and dept_selecionado != "Todos":
        dept_user = dept_selecionado.strip().upper()
        df_users = df_users[
            (df_users['departamento'].astype(str).str.strip().str.upper() == dept_user) | 
            (df_users['nivel'].astype(str).str.strip().str.upper() == dept_user)
        ]
    
    lista_colaboradores = sorted(df_users['nome'].dropna().unique().tolist()) if not df_users.empty else []
    opcoes_sdr = ["Selecione..."] + lista_colaboradores

    # ==========================================================
    # 2. SELEÇÃO DINÂMICA (FORA DO FORMULÁRIO)
    # ==========================================================
    with st.container(border=True):
        st.subheader("👤 Identificação da Chamada")
        c1, c2, c3 = st.columns([2, 1.5, 1.5])
        
        sdr_escolhido = c1.selectbox("Colaborador Auditado", options=opcoes_sdr)
        link_selene = c2.text_input("URL da Gravação (Selene/Zoom)", placeholder="http://...")
        link_nectar = c3.text_input("URL do CRM (Nectar)", placeholder="http://...")

    if sdr_escolhido == "Selecione...":
        st.info("👆 Selecione um colaborador acima para carregar o checklist correspondente.")
        return

    # 🔎 DESCOBRINDO O DEPARTAMENTO DO COLABORADOR
    dept_do_colaborador = "Todos"
    if not df_users.empty:
        linha_colab = df_users[df_users['nome'] == sdr_escolhido]
        if not linha_colab.empty:
            dept_do_colaborador = str(linha_colab.iloc[0].get('departamento', 'Todos')).strip()

    st.markdown(f"**Setor do Colaborador:** `{dept_do_colaborador}`")

    # 🎯 FILTRANDO OS CRITÉRIOS
    if not df_criterios.empty:
        df_criterios = df_criterios[
            (df_criterios['departamento'].astype(str).str.strip().str.upper() == dept_do_colaborador.upper()) | 
            (df_criterios['departamento'].astype(str).str.strip().str.title() == 'Todos')
        ].copy()

    # ==========================================================
    # 3. FORMULÁRIO DE MONITORIA
    # ==========================================================
    with st.form("form_monitoria_v5", clear_on_submit=False):
        respostas = {}
        grupos = df_criterios['grupo'].unique() if 'grupo' in df_criterios.columns else ["Geral"]

        for grupo in grupos:
            with st.expander(f"📂 {str(grupo).upper()}", expanded=True):
                itens_grupo = df_criterios[df_criterios['grupo'] == grupo]
                
                for _, row in itens_grupo.iterrows():
                    id_c = row['id']
                    nome_c = row['nome']
                    peso_c = int(row.get('peso', 1))
                    eh_fatal = bool(row.get('eh_fatal', False))
                    
                    st.markdown(f"**{nome_c}** {'🚩' if eh_fatal else ''} <small>(Peso: {peso_c})</small>", unsafe_allow_html=True)
                    
                    col_res, col_com, col_img = st.columns([1.5, 2, 1.2])
                    v_res = col_res.radio(f"Status {id_c}", ["C", "NC", "NC Grave", "NSA"], index=0, horizontal=True, label_visibility="collapsed", key=f"rad_{id_c}")
                    v_com = col_com.text_input("Comentário", placeholder="Justificativa (Opcional)...", label_visibility="collapsed", key=f"com_{id_c}")
                    v_img = col_img.file_uploader("Evidência", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed", key=f"file_{id_c}")
                    
                    respostas[nome_c] = {
                        "valor": v_res, "peso": peso_c, "eh_fatal": eh_fatal,
                        "comentario": v_com, "arquivo": v_img,
                        "nome_original": v_img.name if v_img else None
                    }
                    st.divider()

        # Puxa o rascunho da IA se houver
        texto_inicial = st.session_state.get('feedback_sugerido', '')
        observacoes = st.text_area("Pontos Positivos e Planos de Ação:", value=texto_inicial, height=150)

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn_ia, col_btn_salvar = st.columns(2)
        
        # 🤖 BOTÃO 1: GERAR PDI COM IA
        btn_ia = col_btn_ia.form_submit_button("🤖 Sugerir PDI com IA (Rascunho)", use_container_width=True)
        # 🚀 BOTÃO 2: FINALIZAR
        btn_salvar = col_btn_salvar.form_submit_button("🚀 Finalizar e Enviar Monitoria", use_container_width=True, type="primary")

        # --- LÓGICA DO BOTÃO DA IA ---
        if btn_ia:
            erros_para_ia = {nome: item['comentario'] for nome, item in respostas.items() if item['valor'] in ["NC", "NC Grave"]}
            if not erros_para_ia:
                st.info("✨ Nenhum erro marcado. A IA sugere enviar um feedback de parabéns!")
                st.session_state['feedback_sugerido'] = f"Excelente atendimento, {sdr_escolhido}! Você seguiu os processos com perfeição. Parabéns pelo resultado e continue assim!"
                st.rerun()
            else:
                with st.spinner("🧠 Lendo os erros e criando o plano de ação..."):
                    sugestao = sugerir_pdi_ia(erros_para_ia, dept_do_colaborador)
                    st.session_state['feedback_sugerido'] = sugestao
                    st.rerun() # Recarrega para mostrar o texto na caixa de observações

        # --- LÓGICA DO BOTÃO DE SALVAR ---
        if btn_salvar:
            with st.spinner("Calculando nota e processando evidências..."):
                total_maximo_ponderado = 0.0
                total_conquistado_ponderado = 0.0
                fatal_detectado = False
                detalhes_finais = {}
                erro_upload = False

                for nome, item in respostas.items():
                    res = item["valor"]
                    peso = item["peso"]
                    fatal = item["eh_fatal"]
                    
                    url_publica = None
                    if item["arquivo"]:
                        try:
                            f = item["arquivo"]
                            ext = f.name.split('.')[-1].lower() 
                            nome_bucket = f"prova_{uuid.uuid4().hex[:10]}.{ext}"
                            supabase.storage.from_("evidencias").upload(path=nome_bucket, file=f.getvalue(), file_options={"content-type": f.type})
                            
                            res_url = supabase.storage.from_("evidencias").get_public_url(nome_bucket)
                            if isinstance(res_url, str):
                                url_publica = res_url
                            else:
                                url_publica = getattr(res_url, 'public_url', str(res_url))
                                
                        except Exception as e:
                            st.error(f"🛑 Erro no upload: {e}")
                            erro_upload = True

                    if res != "NSA":
                        total_maximo_ponderado += peso
                        if res == "C":
                            total_conquistado_ponderado += peso
                        else:
                            if fatal: fatal_detectado = True
                    
                    if res == "NC Grave": fatal_detectado = True

                    # Dados da foto salvos internamente no JSON (Sem quebrar o banco)
                    detalhes_finais[nome] = {
                        "nota": res, "comentario": item["comentario"],
                        "peso_aplicado": peso, "foi_fatal": fatal, 
                        "url_arquivo": url_publica,
                        "evidencia_anexada": True if url_publica else False,
                        "arquivo": item["nome_original"]
                    }

                if erro_upload: st.stop()

                nota_final = 0 if fatal_detectado else (total_conquistado_ponderado / total_maximo_ponderado * 100) if total_maximo_ponderado > 0 else 100

                # Payload limpo de colunas inexistentes
                payload = {
                    "sdr": sdr_escolhido,
                    "departamento": dept_do_colaborador,
                    "nota": int(round(nota_final)),
                    "link_selene": link_selene,
                    "link_nectar": link_nectar,
                    "observacoes": observacoes,
                    "monitor_responsavel": st.session_state.get('user_nome', 'Sistema'),
                    "detalhes": detalhes_finais
                }

                sucesso, msg = salvar_monitoria_auditada(payload)
                
                if sucesso:
                    # Limpa o feedback sugerido do cache para a próxima monitoria
                    if 'feedback_sugerido' in st.session_state:
                        del st.session_state['feedback_sugerido']

                    st.success(f"✅ Monitoria salva com nota {payload['nota']}%!")
                    
                    # ==========================================================
                    # 🔔 GATILHOS DE NOTIFICAÇÃO (UNIFICADOS E COMPLETOS)
                    # ==========================================================
                    try:
                        # 1. Sempre avisa o SDR que ele tem uma nova nota
                        supabase.table("notificacoes").insert({
                            "usuario": sdr_escolhido, 
                            "mensagem": f"📊 Você recebeu uma nova avaliação de qualidade! Nota: {payload['nota']}%.", 
                            "lida": False
                        }).execute()

                        # 2. Regras de Medalhas (Gamificação)
                        if payload['nota'] == 100:
                            # -------- LÓGICA DO COMBO (ON FIRE) --------
                            res_historico = supabase.table("monitorias").select("nota").eq("sdr", sdr_escolhido).order("criado_em", desc=True).limit(3).execute()
                            ultimas_notas = [float(r['nota']) for r in res_historico.data] if res_historico.data else []
                            
                            # Se ele tiver pelo menos 3 e as 3 forem nota 100...
                            if len(ultimas_notas) == 3 and all(n == 100.0 for n in ultimas_notas):
                                msg_medalha = "🔥 ON FIRE! Absoluto! Você conquistou 3 monitorias seguidas com nota 100%!"
                            else:
                                msg_medalha = "🎯 PARABÉNS! Você conquistou a Medalha Sniper (Nota 100%)."
                                
                            supabase.table("notificacoes").insert({
                                "usuario": sdr_escolhido, 
                                "mensagem": msg_medalha, 
                                "lida": False
                            }).execute()
                            # -------------------------------------------
                            
                        elif not fatal_detectado and payload['nota'] > 0:
                            supabase.table("notificacoes").insert({
                                "usuario": sdr_escolhido, 
                                "mensagem": f"🛡️ Ótimo trabalho! Você finalizou uma call sem erros Fatais (Medalha Muralha).", 
                                "lida": False
                            }).execute()
                    except Exception as e:
                        print(f"Erro silencioso ao gerar notificação: {e}")

                    if fatal_detectado: 
                        st.error("🚨 NOTA ZERO: Um item Crítico/Fatal foi descumprido.")
                        
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {msg}")