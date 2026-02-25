import streamlit as st
import pandas as pd
import time
import uuid
from database import salvar_monitoria_auditada, supabase

def render_nova_monitoria():
    dept_selecionado = st.session_state.get('departamento_selecionado', 'Todos')
    nivel_logado = st.session_state.get('nivel', 'USUARIO').upper()
    
    st.title(f"📝 Nova Monitoria - {dept_selecionado}")
    st.markdown("Preencha o checklist. Itens marcados com 🚩 são **Fatais** e zeram a nota em caso de erro.")
    
    # ==========================================================
    # 1. BUSCA DE CRITÉRIOS (Agora na tabela criterios_qa)
    # ==========================================================
    try:
        # Alterado para buscar da tabela 'criterios_qa'
        res_crit = supabase.table("criterios_qa").select("*").eq("esta_ativo", True).execute()
        df_criterios = pd.DataFrame(res_crit.data) if res_crit.data else pd.DataFrame()
        
        # Adicionado 'email' ao select para permitir o filtro de segurança
        res_users = supabase.table("usuarios").select("nome, email, departamento, nivel").eq("esta_ativo", True).execute()
        df_users = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return

    # ==========================================================
    # 🛡️ TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
    # ==========================================================
    if nivel_logado != "ADMIN" and not df_users.empty:
        if 'email' in df_users.columns:
            df_users = df_users[df_users['email'] != 'admin@grupoacelerador.com.br'].copy()
        elif 'nome' in df_users.columns:
            df_users = df_users[df_users['nome'] != 'admin@grupoacelerador.com.br'].copy()

    # Filtro de Departamento
    if not df_criterios.empty and dept_selecionado != "Todos":
        dept_user = dept_selecionado.strip().upper()
        df_criterios = df_criterios[df_criterios['departamento'].str.upper() == dept_user].copy()

    if df_criterios.empty:
        st.warning(f"⚠️ Nenhum critério ativo encontrado para **{dept_selecionado}**.")
        return

    # Filtro de Colaboradores
    if not df_users.empty and dept_selecionado != "Todos":
        dept_user = dept_selecionado.strip().upper()
        df_users = df_users[(df_users['departamento'].str.upper() == dept_user) | 
                            (df_users['nivel'].str.upper() == dept_user)]
    
    lista_colaboradores = sorted(df_users['nome'].unique().tolist()) if not df_users.empty else []
    opcoes_sdr = ["Selecione..."] + lista_colaboradores

    # ==========================================================
    # 2. FORMULÁRIO DE MONITORIA
    # ==========================================================
    with st.form("form_monitoria_v5", clear_on_submit=True):
        
        with st.container(border=True):
            st.subheader("👤 Identificação da Chamada")
            c1, c2, c3 = st.columns([2, 1.5, 1.5])
            sdr_escolhido = c1.selectbox("Colaborador Auditado", options=opcoes_sdr)
            link_selene = c2.text_input("URL da Gravação (Selene/Zoom)", placeholder="http://...")
            link_nectar = c3.text_input("URL do CRM (Nectar)", placeholder="http://...")

        st.write("##")

        respostas = {}
        grupos = df_criterios['grupo'].unique() if 'grupo' in df_criterios.columns else ["Geral"]

        for grupo in grupos:
            with st.expander(f"📂 {str(grupo).upper()}", expanded=True):
                itens_grupo = df_criterios[df_criterios['grupo'] == grupo]
                
                for _, row in itens_grupo.iterrows():
                    nome_c = row['nome'] # Na nova tabela é 'nome'
                    id_c = row['id']
                    peso_c = int(row.get('peso', 1))
                    eh_fatal = bool(row.get('eh_fatal', False))
                    
                    # Interface: Destaca se o item for fatal
                    label_exibicao = f"🚩 **{nome_c}**" if eh_fatal else f"**{nome_c}**"
                    st.markdown(f"{label_exibicao} <small>(Peso: {peso_c})</small>", unsafe_allow_html=True)
                    
                    col_res, col_com, col_img = st.columns([1.5, 2, 1.2])
                    
                    v_res = col_res.radio(f"Status {id_c}", ["C", "NC", "NC Grave", "NSA"], 
                                           index=0, horizontal=True, label_visibility="collapsed", key=f"rad_{id_c}")
                    
                    v_com = col_com.text_input("Comentário", placeholder="Justificativa...", 
                                              label_visibility="collapsed", key=f"com_{id_c}")
                    
                    v_img = col_img.file_uploader("Evidência", type=['png', 'jpg', 'jpeg'], 
                                                label_visibility="collapsed", key=f"file_{id_c}")
                    
                    # Armazena metadados para o cálculo no submit
                    respostas[nome_c] = {
                        "valor": v_res, 
                        "peso": peso_c, 
                        "eh_fatal": eh_fatal,
                        "comentario": v_com,
                        "arquivo": v_img, 
                        "nome_original": v_img.name if v_img else None
                    }
                    st.divider()

        st.subheader("✍️ Feedback Final")
        observacoes = st.text_area("Pontos Positivos e Planos de Ação:", height=150)

        # ==========================================================
        # 3. PROCESSAMENTO E CÁLCULO PONDERADO
        # ==========================================================
        if st.form_submit_button("🚀 Finalizar e Enviar Monitoria", use_container_width=True, type="primary"):
            
            if sdr_escolhido == "Selecione...":
                st.error("⚠️ Por favor, selecione o colaborador auditado.")
                st.stop()

            # Bloqueia se erro sem comentário
            erros_sem_comentario = [n for n, r in respostas.items() if r['valor'] in ['NC', 'NC Grave'] and not r['comentario']]
            if erros_sem_comentario:
                st.error(f"❌ Justificativa obrigatória para os erros em: {', '.join(erros_sem_comentario)}")
                st.stop()

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
                    
                    # --- UPLOAD DE EVIDÊNCIA ---
                    url_publica = None
                    if item["arquivo"]:
                        try:
                            f = item["arquivo"]
                            ext = f.name.split('.')[-1].lower() 
                            nome_bucket = f"prova_{uuid.uuid4().hex[:10]}.{ext}"
                            supabase.storage.from_("evidencias").upload(
                                path=nome_bucket, 
                                file=f.getvalue(),
                                file_options={"content-type": f.type}
                            )
                            res_url = supabase.storage.from_("evidencias").get_public_url(nome_bucket)
                            url_publica = res_url.public_url
                        except Exception as e:
                            st.error(f"🛑 Erro no upload: {e}")
                            erro_upload = True

                    # --- LÓGICA DE PONTUAÇÃO PONDERADA ---
                    if res != "NSA":
                        total_maximo_ponderado += peso
                        if res == "C":
                            total_conquistado_ponderado += peso
                        else:
                            # Se for NC ou NC Grave e for item FATAL, ativa a trava
                            if fatal: fatal_detectado = True
                    
                    # Trava legada: NC Grave sempre zera (opcional, mas seguro manter)
                    if res == "NC Grave": fatal_detectado = True

                    # Detalhes para o JSON
                    detalhes_finais[nome] = {
                        "nota": res,
                        "comentario": item["comentario"],
                        "peso_aplicado": peso,
                        "foi_fatal": fatal,
                        "url_arquivo": url_publica
                    }

                if erro_upload: st.stop()

                # --- CÁLCULO FINAL ---
                if fatal_detectado:
                    nota_final = 0
                else:
                    nota_final = (total_conquistado_ponderado / total_maximo_ponderado * 100) if total_maximo_ponderado > 0 else 100

                payload = {
                    "sdr": sdr_escolhido,
                    "departamento": dept_selecionado,
                    "nota": int(round(nota_final)),
                    "link_selene": link_selene,
                    "link_nectar": link_nectar,
                    "observacoes": observacoes,
                    "monitor_responsavel": st.session_state.get('user_nome', 'Sistema'),
                    "detalhes": detalhes_finais
                }

                sucesso, msg = salvar_monitoria_auditada(payload)
                
                if sucesso:
                    st.success(f"✅ Monitoria finalizada com nota {payload['nota']}%!")
                    if fatal_detectado: 
                        st.error("🚨 NOTA ZERO: Um item Crítico/Fatal foi descumprido.")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {msg}")