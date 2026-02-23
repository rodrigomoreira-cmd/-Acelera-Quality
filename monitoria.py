import streamlit as st
import pandas as pd
import time
import uuid
from database import salvar_monitoria_auditada, supabase

def render_nova_monitoria():
    dept_selecionado = st.session_state.get('departamento_selecionado', 'Todos')
    
    st.title(f"📝 Nova Monitoria - {dept_selecionado}")
    st.markdown("Preencha o checklist abaixo para avaliar a performance do colaborador.")
    
    # ==========================================================
    # 1. BUSCA E FILTRO DE CRITÉRIOS
    # ==========================================================
    try:
        res_crit = supabase.table("config_criterios").select("*").eq("ativo", True).execute()
        df_criterios = pd.DataFrame(res_crit.data) if res_crit.data else pd.DataFrame()
        
        res_users = supabase.table("usuarios").select("nome, departamento, nivel").eq("esta_ativo", True).execute()
        df_users = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return

    # Filtros
    if not df_criterios.empty and dept_selecionado != "Todos":
        dept_user = dept_selecionado.strip().upper()
        df_criterios = df_criterios[df_criterios['departamento'].str.upper() == dept_user].copy()

    if df_criterios.empty:
        st.warning(f"⚠️ Nenhum critério ativo encontrado para **{dept_selecionado}**.")
        return

    if not df_users.empty and dept_selecionado != "Todos":
        dept_user = dept_selecionado.strip().upper()
        df_users = df_users[(df_users['departamento'].str.upper() == dept_user) | 
                            (df_users['nivel'].str.upper() == dept_user)]
    
    lista_colaboradores = sorted(df_users['nome'].unique().tolist()) if not df_users.empty else []
    opcoes_sdr = ["Selecione..."] + lista_colaboradores

    # ==========================================================
    # 2. FORMULÁRIO DE MONITORIA
    # ==========================================================
    with st.form("form_monitoria_v4", clear_on_submit=True):
        
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
            with st.expander(f"📂 {grupo.upper()}", expanded=True):
                itens_grupo = df_criterios[df_criterios['grupo'] == grupo]
                
                for _, row in itens_grupo.iterrows():
                    nome_c = row['nome_criterio']
                    id_c = row['id']
                    peso_c = float(row.get('peso', 1.0))
                    
                    st.markdown(f"**{nome_c}**")
                    col_res, col_com, col_img = st.columns([1.5, 2, 1.2])
                    
                    v_res = col_res.radio(f"Status {id_c}", ["C", "NC", "NC Grave", "NSA"], 
                                         index=0, horizontal=True, label_visibility="collapsed", key=f"rad_{id_c}")
                    
                    v_com = col_com.text_input("Comentário", placeholder="Justificativa...", 
                                             label_visibility="collapsed", key=f"com_{id_c}")
                    
                    v_img = col_img.file_uploader("Evidência", type=['png', 'jpg', 'jpeg'], 
                                                label_visibility="collapsed", key=f"file_{id_c}")
                    
                    respostas[nome_c] = {
                        "valor": v_res, "peso": peso_c, "comentario": v_com,
                        "arquivo": v_img, "nome_original": v_img.name if v_img else None
                    }
                    st.divider()

        st.subheader("✍️ Feedback Final")
        observacoes = st.text_area("Pontos Positivos e Planos de Ação:", height=150)

        # ==========================================================
        # 3. PROCESSAMENTO E UPLOAD DE DADOS
        # ==========================================================
        if st.form_submit_button("🚀 Finalizar e Enviar Monitoria", use_container_width=True, type="primary"):
            
            if sdr_escolhido == "Selecione...":
                st.error("⚠️ Por favor, selecione o colaborador auditado.")
                st.stop()

            # Bloqueia se der erro (NC) e não colocar comentário
            erros_sem_comentario = [n for n, r in respostas.items() if r['valor'] in ['NC', 'NC Grave'] and not r['comentario']]
            if erros_sem_comentario:
                st.error(f"❌ Justificativa obrigatória para os erros em: {', '.join(erros_sem_comentario)}")
                st.stop()

            with st.spinner("Salvando avaliação e limpando nomes de arquivos para a nuvem... ☁️"):
                total_maximo = 0.0
                total_conquistado = 0.0
                nc_grave_detectado = False
                detalhes_finais = {}
                erro_upload = False # Variável para travar se o Supabase recusar a foto

                for nome, item in respostas.items():
                    res = item["valor"]
                    peso = item["peso"]
                    
                    # ----------------------------------------------------
                    # 🛠️ UPLOAD BLINDADO (Remove espaços e acentos)
                    # ----------------------------------------------------
                    url_publica = None
                    if item["arquivo"]:
                        try:
                            f = item["arquivo"]
                            # Pega só a extensão (.png, .jpg)
                            ext = f.name.split('.')[-1].lower() 
                            # Cria um nome 100% limpo, ex: prova_a1b2c3d4.png
                            nome_bucket = f"prova_{uuid.uuid4().hex[:10]}.{ext}"
                            
                            # Faz o upload
                            supabase.storage.from_("evidencias").upload(
                                path=nome_bucket, 
                                file=f.getvalue(),
                                file_options={"content-type": f.type}
                            )
                            
                            # Gera o link público
                            res_url = supabase.storage.from_("evidencias").get_public_url(nome_bucket)
                            url_publica = res_url.public_url if hasattr(res_url, 'public_url') else str(res_url)
                            
                        except Exception as e:
                            st.error(f"🛑 Erro Técnico ao enviar '{item['nome_original']}': {e}")
                            erro_upload = True
                            st.stop() # Para o salvamento para não gerar monitoria defeituosa

                    # ----------------------------------------------------
                    # Lógica de Pontuação
                    if res == "NC Grave": nc_grave_detectado = True
                    
                    if res != "NSA":
                        total_maximo += peso
                        if res == "C":
                            total_conquistado += peso

                    # Montagem do JSON
                    detalhes_finais[nome] = {
                        "nota": res,
                        "comentario": item["comentario"],
                        "arquivo": item["nome_original"], # Mantemos o nome bonito só para exibir
                        "url_arquivo": url_publica,
                        "evidencia_anexada": True if url_publica else False
                    }

                # Se houve erro no upload, não salva a monitoria
                if erro_upload:
                    st.stop()

                # Cálculo da Nota
                nota_final = 0 if nc_grave_detectado else (
                    (total_conquistado / total_maximo * 100) if total_maximo > 0 else 100
                )

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
                    st.success(f"✅ Monitoria de {sdr_escolhido} finalizada com nota {payload['nota']}%!")
                    if nc_grave_detectado: st.warning("⚠️ Nota zero aplicada devido a NC Grave.")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar no banco de dados: {msg}")