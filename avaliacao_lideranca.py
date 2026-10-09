import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria
import time
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import unicodedata
from fpdf import FPDF
import os

# ==========================================================
# FUNÇÕES AUXILIARES (PDF PREMIUM E CALENDÁRIO)
# ==========================================================
def normalizar_texto(texto):
    """Remove acentos para evitar bugs na geração do PDF com o FPDF"""
    if not isinstance(texto, str):
        return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def gerar_pdf_lideranca(gestor_nome, ciclo, nota_geral, total_votos, medias_criterios, comentarios_validos, ponto_forte, ponto_atencao):
    """Constrói o documento PDF no padrão premium (estilo PDI)"""
    pdf = FPDF()
    pdf.add_page()
    
    # Paleta de Cores da Marca
    LARANJA = (221, 109, 0)
    PRETO = (50, 50, 50)
    CINZA_CLARO = (240, 240, 240)
    BRANCO = (255, 255, 255)

    # 1. Cabeçalho com Logo
    if os.path.exists("assets/logo_pdf.png"):
        pdf.image("assets/logo_pdf.png", x=10, y=10, w=35)
        pdf.ln(12)
    else:
        pdf.ln(5)
    
    # 2. Título Principal
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(*LARANJA)
    pdf.cell(0, 10, normalizar_texto("DIAGNÓSTICO 360 - AVALIAÇÃO DE LIDERANÇA"), ln=True, align='C')
    
    pdf.set_font("Arial", 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, normalizar_texto(f"Ciclo: {ciclo} | Data de Emissão: {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align='C')
    pdf.ln(10)

    # 3. Caixa de Resumo do Gestor (Estilo Tabela)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(*CINZA_CLARO)
    pdf.set_text_color(*PRETO)
    pdf.cell(0, 10, normalizar_texto(f" GESTOR AVALIADO: {gestor_nome.upper()}"), border=1, ln=True, fill=True)
    
    # 4. Painel de KPIs (Métricas Principais)
    pdf.set_font("Arial", '', 11)
    # Linha 1
    pdf.cell(95, 10, normalizar_texto(f" Nota Média Geral: {nota_geral:.2f} / 5.00"), border=1)
    pdf.cell(95, 10, normalizar_texto(f" Avaliações Recebidas: {total_votos}"), border=1, ln=True)
    # Linha 2
    pdf.cell(95, 10, normalizar_texto(f" Maior Força: {ponto_forte}"), border=1)
    pdf.cell(95, 10, normalizar_texto(f" Ponto de Atenção: {ponto_atencao}"), border=1, ln=True)
    pdf.ln(10)

    # 5. Tabela Detalhada de Competências
    pdf.set_font("Arial", 'B', 13)
    pdf.set_text_color(*LARANJA)
    pdf.cell(0, 10, normalizar_texto("MAPA DE COMPETÊNCIAS"), ln=True)
    
    # Cabeçalho da Tabela
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(*LARANJA)
    pdf.set_text_color(*BRANCO)
    pdf.cell(150, 10, normalizar_texto(" Critério Avaliado"), border=1, fill=True)
    pdf.cell(40, 10, normalizar_texto(" Nota Média"), border=1, fill=True, align='C', ln=True)

    # Linhas da Tabela
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(*PRETO)
    fill = False
    for crit, nota in medias_criterios.items():
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(150, 10, normalizar_texto(f" {crit}"), border=1, fill=fill)
        pdf.cell(40, 10, normalizar_texto(f"{nota:.2f}"), border=1, align='C', fill=fill, ln=True)
        fill = not fill # Alterna a cor da linha (Zebrado)

    pdf.ln(10)

    # 6. Bloco de Comentários Qualitativos
    pdf.set_font("Arial", 'B', 13)
    pdf.set_text_color(*LARANJA)
    pdf.cell(0, 10, normalizar_texto("FEEDBACKS ANÔNIMOS DA EQUIPE"), ln=True)
    
    pdf.set_font("Arial", 'I', 11)
    pdf.set_text_color(*PRETO)
    
    if not comentarios_validos:
        pdf.set_fill_color(*CINZA_CLARO)
        pdf.cell(0, 10, normalizar_texto(" Nenhuma observação registrada ou liberada para este ciclo."), border=1, ln=True, fill=True)
    else:
        for c in comentarios_validos:
            pdf.set_fill_color(250, 250, 250)
            pdf.multi_cell(0, 8, normalizar_texto(f'"{c}"'), border=1, fill=True)
            pdf.ln(3)

    return pdf.output(dest="S").encode("latin-1")

def obter_ciclo_atual():
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year
    
    janela_aberta = mes in [3, 6, 9, 12]
    
    if mes <= 3: ciclo = f"1º Trimestre {ano}"
    elif mes <= 6: ciclo = f"2º Trimestre {ano}"
    elif mes <= 9: ciclo = f"3º Trimestre {ano}"
    else: ciclo = f"4º Trimestre {ano}"
    
    return ciclo, janela_aberta, mes

# ==========================================================
# TELA DE VOTAÇÃO (SDRs)
# ==========================================================
def render_avaliacao_lideranca():
    st.title("⬆️ Avaliação da Liderança (Bottom-Up)")
    
    ciclo_atual, janela_aberta, mes_atual = obter_ciclo_atual()
    nome_logado = st.session_state.get('user_nome', 'Desconhecido')

    if not janela_aberta:
        st.warning(f"🔒 **Janela Fechada:** A avaliação do **{ciclo_atual}** só será liberada no fechamento do trimestre (Março, Junho, Setembro ou Dezembro).")
        st.info("Fique tranquilo, o sistema enviará um alerta automático no menu quando o período for aberto!")
        return

    st.markdown(f"✅ **Janela Aberta!** Chegou a hora de avaliar a sua liderança referente ao **{ciclo_atual}**. Seu feedback é **confidencial** e fundamental.")

    try:
        res_users = supabase.table("usuarios").select("nome, nivel, departamento").in_("nivel", ["GESTAO", "GERENCIA", "ADMIN"]).eq("esta_ativo", True).execute()
        df_gestores = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame()
    except: df_gestores = pd.DataFrame()

    if df_gestores.empty:
        st.warning("Nenhum gestor encontrado no sistema para avaliação.")
        return
        
    df_gestores = df_gestores[~df_gestores['nome'].str.contains('admin@', case=False, na=False)]
    lista_gestores = sorted(df_gestores['nome'].dropna().unique().tolist())

    try:
        res_crit = supabase.table("criterios_lideranca").select("*").eq("esta_ativo", True).execute()
        lista_crit = res_crit.data if res_crit.data else []
    except: lista_crit = []

    if not lista_crit:
        st.error("Nenhum critério configurado no momento.")
        return

    with st.container(border=True):
        st.subheader("📋 Preencher Avaliação")
        gestor_selecionado = st.selectbox("Quem você vai avaliar?", ["Selecione..."] + lista_gestores)

    if gestor_selecionado == "Selecione...":
        st.info("👆 Selecione o seu gestor acima para carregar o formulário.")
        return

    try:
        trava_res = supabase.table("avaliacoes_lideranca").select("id").eq("avaliador_nome", nome_logado).eq("gestor_avaliado", gestor_selecionado).eq("ciclo_avaliacao", ciclo_atual).execute()
        ja_avaliou = len(trava_res.data) > 0
    except: ja_avaliou = False

    if ja_avaliou:
        st.success(f"✅ Você já avaliou **{gestor_selecionado}** neste ciclo ({ciclo_atual}). O RH agradece o seu feedback estruturado!")
        return

    with st.form("form_aval_lideranca", clear_on_submit=True):
        st.markdown(f"**Avaliando Gestor(a):** `{gestor_selecionado}`")
        st.caption("A régua de nota vai de 1 (Necessita muita melhoria) a 5 (Excelente / Mandou muito bem)")
        
        respostas = {}
        for crit in lista_crit:
            st.markdown(f"#### {crit['nome']}")
            c_slider, c_text = st.columns([1, 2])
            val = c_slider.slider("Nota", 1, 5, 3, key=f"slider_lid_{crit['id']}", label_visibility="collapsed")
            respostas[crit['nome']] = val
            c_text.write(f"*{crit.get('descricao', '')}*")
            st.divider()

        comentarios = st.text_area("Comentários e Sugestões (Opcional)", placeholder="Deixe um feedback construtivo. O gestor NÃO saberá que foi você quem escreveu.", height=150)

        st.info("🔒 **Fique tranquilo!** O gestor terá acesso apenas à média das notas e aos comentários de forma 100% anônima.")
        btn_salvar = st.form_submit_button("🚀 Enviar Avaliação Confidencial", type="primary", use_container_width=True)

        if btn_salvar:
            media = sum(respostas.values()) / len(respostas)
            
            # --- INTELIGÊNCIA ARTIFICIAL: ANÁLISE DE CLIMA ---
            sentimento_ia = "⚪ Sem Comentário"
            resumo_ia = ""
            
            if comentarios.strip():
                with st.spinner("🤖 Processando feedback com IA..."):
                    try:
                        from analise_ia import analisar_clima_lideranca
                        sentimento_ia, resumo_ia = analisar_clima_lideranca(comentarios.strip())
                    except Exception as e:
                        print(f"Erro IA: {e}")
            # --------------------------------------------------

            payload = {
                "avaliador_nome": nome_logado, "gestor_avaliado": gestor_selecionado,
                "ciclo_avaliacao": ciclo_atual, "detalhes": respostas,
                "media_nota": round(media, 2), "comentarios": comentarios.strip(),
                "sentimento_ia": sentimento_ia, # Salvando a tag da IA
                "resumo_ia": resumo_ia          # Salvando o resumo da IA
            }

            try:
                supabase.table("avaliacoes_lideranca").insert(payload).execute()
                registrar_auditoria("AVALIAÇÃO LIDERANÇA", f"Avaliou anonimamente um gestor no ciclo {ciclo_atual}", "N/A", nome_logado)
                
                try:
                    msg_notif = f"📊 Você recebeu uma nova avaliação anônima da sua equipe referente ao {ciclo_atual}!"
                    supabase.table("notificacoes").insert({
                        "usuario": gestor_selecionado, 
                        "mensagem": msg_notif, 
                        "lida": False
                    }).execute()
                except Exception as e_notif:
                    print(f"Erro ao enviar notificação: {e_notif}")
                
                st.toast("✅ Avaliação enviada com sucesso!", icon="🎉")
                st.balloons()
                time.sleep(2)
                st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")

# ==========================================================
# TELA DE RESULTADOS PREMIUM (Dashboard do Gestor/Admin)
# ==========================================================
def render_dashboard_lideranca():
    st.title("📊 Dashboard de Liderança (360°)")
    st.markdown("Visão consolidada da percepção da equipe sobre a gestão.")

    nome_logado = st.session_state.get('user_nome', 'Desconhecido')
    nivel_logado = st.session_state.get('nivel', 'GESTAO')

    c1, c2 = st.columns(2)
    ano_atual = datetime.now().year
    ciclos = [f"1º Trimestre {ano_atual}", f"2º Trimestre {ano_atual}", f"3º Trimestre {ano_atual}", f"4º Trimestre {ano_atual}"]
    ciclo_atual_nome, _, _ = obter_ciclo_atual()
    idx_padrao = ciclos.index(ciclo_atual_nome) if ciclo_atual_nome in ciclos else 0
    
    ciclo_sel = c1.selectbox("Selecione o Ciclo:", ciclos, index=idx_padrao)

    if nivel_logado == "ADMIN":
        try:
            res_todos = supabase.table("avaliacoes_lideranca").select("gestor_avaliado").eq("ciclo_avaliacao", ciclo_sel).execute()
            lista_avaliados = sorted(list(set([x['gestor_avaliado'] for x in res_todos.data]))) if res_todos.data else []
        except: lista_avaliados = []
        
        gestor_sel = c2.selectbox("Filtrar Gestor:", ["Todos da Empresa"] + lista_avaliados)
    else:
        gestor_sel = nome_logado
        c2.selectbox("Filtrar Gestor:", [nome_logado], disabled=True)

    try:
        query = supabase.table("avaliacoes_lideranca").select("*").eq("ciclo_avaliacao", ciclo_sel)
        if gestor_sel != "Todos da Empresa":
            query = query.eq("gestor_avaliado", gestor_sel)
            
        res = query.execute()
        df_notas = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: df_notas = pd.DataFrame()

    if df_notas.empty:
        st.info(f"Nenhuma avaliação encontrada para os filtros selecionados no {ciclo_sel}.")
        return

    detalhes_list = df_notas['detalhes'].tolist()
    df_detalhes = pd.DataFrame(detalhes_list)
    medias_criterios = df_detalhes.mean().round(2)
    
    ponto_forte = medias_criterios.idxmax()
    ponto_atencao = medias_criterios.idxmin()
    nota_geral = df_notas['media_nota'].mean()
    total_votos = len(df_notas)

    # ==========================================================
    # GAMIFICAÇÃO: SELO DE LIDERANÇA INSPIRADORA (NOVO)
    # ==========================================================
    if nota_geral >= 4.5 and total_votos >= 3:
        st.markdown("""
        <div style='background: linear-gradient(90deg, #FFD700 0%, #FFA500 100%); padding: 15px; border-radius: 10px; margin-bottom: 20px; color: #000; display: flex; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <div style='font-size: 40px; margin-right: 15px;'>🏆</div>
            <div>
                <h3 style='margin: 0; color: #000;'>Selo de Liderança Inspiradora</h3>
                <span style='font-size: 14px; font-weight: bold;'>Parabéns! A sua equipe avalia a sua gestão com nível de excelência. Continue a inspirar!</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # ==========================================================

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Nota Média (Geral)", f"{nota_geral:.2f} / 5.0")
    k2.metric("Avaliações Recebidas", total_votos)
    k3.metric("🏆 Maior Força", ponto_forte, f"{medias_criterios[ponto_forte]:.1f}")
    k4.metric("⚠️ Ponto de Atenção", ponto_atencao, f"{medias_criterios[ponto_atencao]:.1f}", delta_color="inverse")

    st.divider()

    g1, g2 = st.columns([1, 1])

    with g1:
        st.markdown("#### 🎯 Mapa de Competências (Radar)")
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=medias_criterios.values.tolist() + [medias_criterios.values[0]],
            theta=medias_criterios.index.tolist() + [medias_criterios.index[0]],
            fill='toself', 
            line_color='#dd6d00', # CORRIGIDO PARA LARANJA
            name='Nota Média',
            hovertemplate='<b>%{theta}</b>: %{r}<extra></extra>' 
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])), 
            showlegend=False, paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
            margin=dict(l=40, r=40, t=20, b=20)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with g2:
        st.markdown("#### 📊 Distribuição das Notas por Critério")
        df_barras = medias_criterios.reset_index()
        df_barras.columns = ['Critério', 'Média']
        df_barras = df_barras.sort_values(by='Média', ascending=True)
        
        # CORRIGIDO PARA ESCALA DE CORES LARANJA ('Oranges')
        fig_bar = px.bar(df_barras, x='Média', y='Critério', orientation='h', text='Média', color='Média', color_continuous_scale='Oranges')
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
            xaxis=dict(range=[0, 5.5], showgrid=False), yaxis=dict(title=""),
            coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=20)
        )
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ==========================================================
    # FEEDBACK ABERTO COM INTELIGÊNCIA ARTIFICIAL
    # ==========================================================
    st.subheader("💬 Feedback Aberto da Equipe (Análise com IA 🤖)")
    
    # Preparando os comentários válidos para o PDF e exibição
    if 'comentarios' in df_notas.columns:
        df_com_feedback = df_notas.dropna(subset=['comentarios'])
        df_com_feedback = df_com_feedback[df_com_feedback['comentarios'].str.strip() != ""]
        comentarios_validos = df_com_feedback['comentarios'].tolist() if not df_com_feedback.empty else []
    else:
        df_com_feedback = pd.DataFrame()
        comentarios_validos = []

    if total_votos < 3 and nivel_logado != "ADMIN":
        st.warning("⚠️ **Confidencialidade:** Os comentários abertos só serão liberados para visualização do gestor após receberem pelo menos 3 avaliações, garantindo assim a segurança psicológica e o anonimato da equipe.")
    else:
        if df_com_feedback.empty:
            st.info("Nenhum comentário por escrito foi deixado neste ciclo.")
        else:
            for _, row in df_com_feedback.iterrows():
                texto = row['comentarios']
                tag_ia = row.get('sentimento_ia', '⚪ Sem IA')
                if pd.isna(tag_ia): tag_ia = '⚪ Sem IA'
                
                resumo_ia = row.get('resumo_ia', '')
                if pd.isna(resumo_ia): resumo_ia = ''
                
                # Exibição estilizada com a Tag da IA e Resumo
                st.markdown(f"""
                <div style='background-color:#1e1e1e; padding:15px; border-radius:8px; margin-bottom:10px; border-left: 4px solid #dd6d00;'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
                        <span style='font-size: 14px; color: #aaa;'><b>IA Classificou:</b> {tag_ia}</span>
                    </div>
                    <i>"{texto}"</i>
                    <br><br>
                    <span style='font-size: 13px; color: #888;'><b>🧠 Resumo IA:</b> {resumo_ia}</span>
                </div>
                """, unsafe_allow_html=True)

    # ==========================================================
    # BOTÃO DE EXPORTAR PDF
    # ==========================================================
    st.divider()
    st.markdown("### 📥 Exportar Relatório Oficial")
    
    pdf_bytes = gerar_pdf_lideranca(
        gestor_nome=gestor_sel,
        ciclo=ciclo_sel,
        nota_geral=nota_geral,
        total_votos=total_votos,
        medias_criterios=medias_criterios,
        comentarios_validos=comentarios_validos, # O PDF continua recebendo só o texto limpo
        ponto_forte=ponto_forte,
        ponto_atencao=ponto_atencao
    )
    
    st.download_button(
        label=f"📄 Baixar PDF - {gestor_sel}",
        data=pdf_bytes,
        file_name=f"Relatorio_360_{gestor_sel.replace(' ', '_')}_{ciclo_sel[:2]}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

    registrar_auditoria("ACESSO DASHBOARD LIDERANÇA", f"Visualizou os resultados de {gestor_sel} ({ciclo_sel})", "N/A", nome_logado)