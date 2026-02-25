import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_all_records_db, supabase, registrar_auditoria
from datetime import datetime
import time
from fpdf import FPDF
import unicodedata

# ==========================================================
# FUNÇÕES DE PDF
# ==========================================================
def limpar_texto_para_pdf(txt):
    if not isinstance(txt, str): return ""
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt.encode('latin-1', 'ignore').decode('latin-1')

def gerar_pdf_pdi(nome_colab, mes, gestor, nota_tec, nota_comp, perfil, detalhes, observacoes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Relatorio de PDI - Acelera Quality", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"Colaborador: {limpar_texto_para_pdf(nome_colab)}", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 8, txt=f"Mes de Referencia: {mes}", ln=True)
    pdf.cell(200, 8, txt=f"Avaliador: {limpar_texto_para_pdf(gestor)}", ln=True)
    pdf.cell(200, 8, txt=f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Resumo de Desempenho:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 8, txt=f"Media Tecnica (QA): {nota_tec:.1f}%", ln=True)
    pdf.cell(200, 8, txt=f"Media Comportamental: {nota_comp:.1f}%", ln=True)
    pdf.cell(200, 8, txt=f"Classificacao: {limpar_texto_para_pdf(perfil)}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Detalhamento Comportamental:", ln=True)
    pdf.set_font("Arial", '', 12)
    for k, v in detalhes.items():
        pdf.cell(200, 8, txt=f"{limpar_texto_para_pdf(k)}: {v} / 5", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Plano de Acao e Feedback:", ln=True)
    pdf.set_font("Arial", '', 12)
    obs_txt = limpar_texto_para_pdf(observacoes) if observacoes else "Nenhum plano de acao registrado."
    pdf.multi_cell(0, 8, txt=obs_txt)
    try: return pdf.output(dest='S').encode('latin-1')
    except: return bytes(pdf.output())

# ==========================================================
# RENDERIZAÇÃO DA PÁGINA PDI E MATRIZ
# ==========================================================
def render_pdi():
    st.title("🎯 Matriz de Decisão e PDI")
    
    nivel_logado = st.session_state.get('nivel', 'USUARIO').upper()
    nome_logado = st.session_state.get('user_nome', 'Desconhecido').strip()
    dept_logado = st.session_state.get('departamento_selecionado', 'Todos')
    pode_avaliar = nivel_logado in ["ADMIN", "GESTAO", "AUDITOR", "GERENCIA"]

    # 1. Busca de Dados Brutos
    df_users = get_all_records_db("usuarios")
    df_mon_bruto = get_all_records_db("monitorias")
    df_comp_bruto = get_all_records_db("avaliacoes_comportamentais")
    
    try:
        res_crit = supabase.table("criterios_comportamentais").select("*").eq("esta_ativo", True).order("nome").execute()
        lista_crit_db = res_crit.data if res_crit.data else []
    except: lista_crit_db = []

    if df_users is None or df_users.empty:
        st.warning("Sem usuários cadastrados.")
        return

    # TRAVA DE SEGURANÇA: OCULTAR ADMIN MESTRE
    if nivel_logado != "ADMIN":
        df_users = df_users[~df_users['nome'].str.contains('admin@grupoacelerador.com.br', na=False, case=False)].copy()

    # Padronização de nomes
    df_users['nome_comp'] = df_users['nome'].astype(str).str.strip().str.upper()

    if not pode_avaliar:
        df_equipe = df_users[df_users['nome_comp'] == nome_logado.upper()]
    else:
        if dept_logado != "Todos":
            df_equipe = df_users[df_users['departamento'].astype(str).str.strip().str.upper() == dept_logado.strip().upper()]
        else:
            df_equipe = df_users.copy()

    lista_colaboradores = sorted(df_equipe['nome'].dropna().unique().tolist())

    with st.container(border=True):
        c1, c2 = st.columns(2)
        colaborador_sel = c1.selectbox("Selecione o Colaborador:", lista_colaboradores, disabled=not pode_avaliar)
        meses_opcoes = [(datetime.now().replace(day=1) - pd.DateOffset(months=i)).strftime('%m/%Y') for i in range(12)]
        mes_sel = c2.selectbox("Mês de Referência:", meses_opcoes)

    if not colaborador_sel: return
    busca_nome = colaborador_sel.strip().upper()

    # Filtros exatos para o colaborador e mês
    df_mon_colab = pd.DataFrame()
    if df_mon_bruto is not None and not df_mon_bruto.empty:
        df_mon_bruto['sdr_comp'] = df_mon_bruto['sdr'].astype(str).str.strip().str.upper()
        df_mon_colab = df_mon_bruto[df_mon_bruto['sdr_comp'] == busca_nome].copy()

    df_comp_colab = pd.DataFrame()
    if df_comp_bruto is not None and not df_comp_bruto.empty:
        df_comp_bruto['sdr_nome_comp'] = df_comp_bruto['sdr_nome'].astype(str).str.strip().str.upper()
        df_comp_colab = df_comp_bruto[df_comp_bruto['sdr_nome_comp'] == busca_nome].copy()

    # Média Técnica do Mês (Tratamento de Datetime fixado)
    nota_tecnica_media = 0.0
    if not df_mon_colab.empty:
        df_mon_colab['criado_em'] = pd.to_datetime(df_mon_colab['criado_em'], errors='coerce')
        df_mon_mes = df_mon_colab[df_mon_colab['criado_em'].dt.strftime('%m/%Y') == mes_sel]
        if not df_mon_mes.empty:
            nota_tecnica_media = pd.to_numeric(df_mon_mes['nota'], errors='coerce').mean()

    # PDI Atual do Mês
    aval_atual = None
    if not df_comp_colab.empty:
        filtro = df_comp_colab[df_comp_colab['mes_referencia'] == mes_sel]
        if not filtro.empty: 
            aval_atual = filtro.iloc[0]

    # Abas
    abas_titulos = ["📊 Dashboard Pessoal", "📝 Preencher Avaliação", "📚 Histórico"]
    if pode_avaliar: abas_titulos.append("🌐 Calibragem da Equipe")
    abas = st.tabs(abas_titulos)

    # ABA 1: DASHBOARD
    with abas[0]:
        if aval_atual is None:
            st.info(f"O colaborador **{colaborador_sel}** ainda não possui avaliação PDI em **{mes_sel}**.")
            st.metric("Média Técnica (QA) do Mês", f"{int(nota_tecnica_media)}%")
        else:
            m_comp_5 = float(aval_atual['media_comportamental'])
            m_comp_100 = (m_comp_5 / 5.0) * 100
            if nota_tecnica_media >= 85 and m_comp_100 >= 80: p, c, s = "⭐ Talento", "#00cc96", "Excelente"
            elif nota_tecnica_media >= 85: p, c, s = "🧩 Especialista", "#ffa500", "Focar em Soft Skills"
            elif m_comp_100 >= 80: p, c, s = "🔥 Alto Potencial", "#1f77b4", "Focar em Técnica (QA)"
            else: p, c, s = "⚠️ Alerta", "#ff4b4b", "Baixo desempenho"

            k1, k2, k3 = st.columns(3)
            k1.metric("Média Técnica (QA)", f"{int(nota_tecnica_media)}%")
            k2.metric("Média Comportamental", f"{int(m_comp_100)}%", f"{m_comp_5:.1f} / 5.0")
            with k3:
                st.markdown(f'<div style="background: linear-gradient(145deg, #262626, #1a1a1a); padding: 15px; border-radius: 12px; border-left: 5px solid {c};"><span style="color: #aaa; font-size: 11px; font-weight: bold; text-transform: uppercase;">Classificação</span><br><span style="color: {c}; font-size: 22px; font-weight: 800;">{p}</span><br><small style="color: white; opacity: 0.7;">{s}</small></div>', unsafe_allow_html=True)

            st.divider()
            gr1, gr2 = st.columns(2)
            with gr1:
                detalhes = aval_atual.get('detalhes', {})
                if detalhes:
                    fig_radar = go.Figure(data=go.Scatterpolar(r=list(detalhes.values()) + [list(detalhes.values())[0]], theta=list(detalhes.keys()) + [list(detalhes.keys())[0]], fill='toself', line_color=c))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_radar, use_container_width=True)
            with gr2:
                st.subheader("💡 Pontos de Melhoria")
                pontos_baixos = [k for k, v in detalhes.items() if v < 4]
                for p_b in pontos_baixos: st.warning(f"**Desenvolver:** {p_b}")
                if not pontos_baixos: st.success("✅ Nenhuma competência crítica identificada.")
                if aval_atual.get('observacoes'): st.info(f"**📝 Plano de Ação:** {aval_atual['observacoes']}")
                pdf_bytes = gerar_pdf_pdi(colaborador_sel, mes_sel, aval_atual.get('gestor_nome','Gestor'), nota_tecnica_media, m_comp_100, p, detalhes, aval_atual.get('observacoes'))
                st.download_button("📥 Baixar PDF do PDI", data=pdf_bytes, file_name=f"PDI_{colaborador_sel}_{mes_sel.replace('/','-')}.pdf", type="primary", use_container_width=True)

    # ABA 2: FORMULÁRIO DE AVALIAÇÃO
    with abas[1]:
        if not pode_avaliar: st.warning("Apenas a liderança pode realizar novas avaliações.")
        elif not lista_crit_db: st.error("Configure os critérios comportamentais antes.")
        else:
            st.subheader(f"Avaliar: {colaborador_sel} | {mes_sel}")
            mostrar_form = True
            if aval_atual is not None:
                st.warning("⚠️ Já existe avaliação neste mês.")
                if not st.checkbox("Liberar formulário para edição", key="edit_check"): mostrar_form = False
            
            if mostrar_form:
                dept_colab = str(df_equipe[df_equipe['nome'] == colaborador_sel].iloc[0].get('departamento', 'Todos')).strip()
                crit_filtrados = [crit for crit in lista_crit_db if crit.get('departamento', 'Todos') in ['Todos', dept_colab]]

                with st.form("form_pdi_v_final", clear_on_submit=True):
                    respostas_comp = {}
                    for i, crit in enumerate(crit_filtrados):
                        if i % 2 == 0: c_l, c_r = st.columns(2)
                        col_alvo = c_l if i % 2 == 0 else c_r
                        nome_c = crit['nome']
                        val_orig = aval_atual.get('detalhes', {}).get(nome_c, 3) if aval_atual is not None else 3
                        respostas_comp[nome_c] = col_alvo.slider(nome_c, 1, 5, int(val_orig))
                    
                    obs_comp = st.text_area("📝 Plano de Ação e Feedback:", value=aval_atual.get('observacoes', '') if aval_atual is not None else "", height=150)
                    
                    btn_submit = st.form_submit_button("💾 Salvar Avaliação PDI", type="primary", use_container_width=True)
                    
                    if btn_submit:
                        media_final = sum(respostas_comp.values()) / len(respostas_comp) if respostas_comp else 0
                        payload = {
                            "sdr_nome": colaborador_sel, 
                            "gestor_nome": nome_logado, 
                            "departamento": dept_colab, 
                            "mes_referencia": mes_sel, 
                            "detalhes": respostas_comp, 
                            "media_comportamental": round(media_final, 2), 
                            "observacoes": obs_comp
                        }
                        try:
                            if aval_atual is not None: 
                                supabase.table("avaliacoes_comportamentais").delete().eq("id", aval_atual['id']).execute()
                            
                            supabase.table("avaliacoes_comportamentais").insert(payload).execute()
                            registrar_auditoria("PDI", f"Avaliou {colaborador_sel} (Mês: {mes_sel})", colaborador_sel, nome_logado)
                            
                            # GATILHO DE MEDALHA MENSAL: TALENTO SUPREMO
                            if nota_tecnica_media >= 85 and media_final >= 4.0:
                                supabase.table("notificacoes").insert({
                                    "usuario": colaborador_sel, 
                                    "mensagem": f"⭐ INCRÍVEL! Você atingiu o Quadrante Verde em {mes_sel}! Medalha Talento Supremo desbloqueada!", 
                                    "lida": False
                                }).execute()

                            st.success("✅ Avaliação salva com sucesso!")
                            get_all_records_db.clear()
                            st.cache_data.clear()
                            time.sleep(1.5); st.rerun()
                        except Exception as e: st.error(f"Erro ao salvar: {e}")

    # ABA 3: HISTÓRICO
    with abas[2]:
        if not df_comp_colab.empty:
            df_h = df_comp_colab.copy()
            df_h['ordem'] = pd.to_datetime(df_h['mes_referencia'], format='%m/%Y', errors='coerce')
            df_h = df_h.dropna(subset=['ordem']).sort_values('ordem')
            evol_list = []
            for _, r in df_h.iterrows():
                m = r['mes_referencia']
                c_sc = (float(r['media_comportamental']) / 5.0) * 100
                df_t = df_mon_colab[pd.to_datetime(df_mon_colab['criado_em'], errors='coerce').dt.strftime('%m/%Y') == m] if not df_mon_colab.empty else pd.DataFrame()
                t_sc = df_t['nota'].astype(float).mean() if not df_t.empty else 0.0
                p_m = "⭐ Talento" if t_sc >= 85 and c_sc >= 80 else ("🧩 Especialista" if t_sc >= 85 else ("🔥 Alto Potencial" if c_sc >= 80 else "⚠️ Alerta"))
                evol_list.append({"Mês": m, "Comport. (%)": round(c_sc, 1), "Técnica (%)": round(t_sc, 1), "Classificação": p_m, "Gestor": r.get('gestor_nome','')})
            
            df_evol = pd.DataFrame(evol_list)
            st.plotly_chart(px.line(df_evol, x="Mês", y=["Comport. (%)", "Técnica (%)"], markers=True).update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, yaxis_range=[0, 105]), use_container_width=True)
            st.dataframe(df_evol, use_container_width=True, hide_index=True)
        else: st.info("Sem histórico disponível.")

    # ABA 4: CALIBRAGEM 9-BOX
    if pode_avaliar:
        with abas[3]:
            dados_matriz = []
            eq_plot = [n for n in df_equipe['nome'].dropna().unique() if nivel_logado == "ADMIN" or n != 'admin@grupoacelerador.com.br']
            for sdr in eq_plot:
                b_eq = sdr.strip().upper(); t_m, c_m = 0.0, 0.0
                df_t_m = df_mon_bruto[(df_mon_bruto['sdr_comp'] == b_eq) & (pd.to_datetime(df_mon_bruto['criado_em'], errors='coerce').dt.strftime('%m/%Y') == mes_sel)] if df_mon_bruto is not None else pd.DataFrame()
                if not df_t_m.empty: t_m = pd.to_numeric(df_t_m['nota'], errors='coerce').mean()
                df_c_m = df_comp_bruto[(df_comp_bruto['sdr_nome_comp'] == b_eq) & (df_comp_bruto['mes_referencia'] == mes_sel)] if df_comp_bruto is not None else pd.DataFrame()
                if not df_c_m.empty: c_m = (float(df_c_m.iloc[0]['media_comportamental']) / 5.0) * 100
                if t_m > 0 or not df_c_m.empty:
                    q = "⭐ Talento" if t_m >= 85 and c_m >= 80 else ("🧩 Especialista" if t_m >= 85 else ("🔥 Alto Potencial" if c_m >= 80 else "⚠️ Alerta"))
                    dados_matriz.append({"Colaborador": sdr, "Técnica (%)": round(t_m, 1), "Comportamento (%)": round(c_m, 1), "Quadrante": q})
            
            if dados_matriz:
                df_m_plot = pd.DataFrame(dados_matriz)
                fig = px.scatter(df_m_plot, x="Comportamento (%)", y="Técnica (%)", text="Colaborador", color="Quadrante", color_discrete_map={"⭐ Talento": "#00cc96", "🧩 Especialista": "#ffa500", "🔥 Alto Potencial": "#1f77b4", "⚠️ Alerta": "#ff4b4b"}, range_x=[-5, 105], range_y=[-5, 105])
                fig.update_layout(shapes=[dict(type="rect", x0=0, y0=0, x1=80, y1=85, fillcolor="#ff4b4b", opacity=0.1, layer="below", line_width=0), dict(type="rect", x0=0, y0=85, x1=80, y1=100, fillcolor="#ffa500", opacity=0.1, layer="below", line_width=0), dict(type="rect", x0=80, y0=0, x1=100, y1=85, fillcolor="#1f77b4", opacity=0.1, layer="below", line_width=0), dict(type="rect", x0=80, y0=85, x1=100, y1=100, fillcolor="#00cc96", opacity=0.1, layer="below", line_width=0)], paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_m_plot, use_container_width=True, hide_index=True)
            else: st.info("Sem dados para calibragem no mês.")