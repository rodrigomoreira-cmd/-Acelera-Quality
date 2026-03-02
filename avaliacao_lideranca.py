import streamlit as st
import pandas as pd
from database import supabase, registrar_auditoria
import time
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# ==========================================================
# INTELIGÊNCIA DE CALENDÁRIO (Trava de Trimestre)
# ==========================================================
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
            payload = {
                "avaliador_nome": nome_logado, "gestor_avaliado": gestor_selecionado,
                "ciclo_avaliacao": ciclo_atual, "detalhes": respostas,
                "media_nota": round(media, 2), "comentarios": comentarios.strip()
            }

            try:
                supabase.table("avaliacoes_lideranca").insert(payload).execute()
                registrar_auditoria("AVALIAÇÃO LIDERANÇA", f"Avaliou anonimamente um gestor no ciclo {ciclo_atual}", "N/A", nome_logado)
                
                # ==========================================================
                # DISPARO DO SINO (NOTIFICAÇÃO) PARA O GESTOR
                # ==========================================================
                try:
                    msg_notif = f"📊 Você recebeu uma nova avaliação anônima da sua equipe referente ao {ciclo_atual}!"
                    supabase.table("notificacoes").insert({
                        "usuario": gestor_selecionado, 
                        "mensagem": msg_notif, 
                        "lida": False
                    }).execute()
                except Exception as e_notif:
                    print(f"Erro ao enviar notificação: {e_notif}")
                # ==========================================================
                
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
            fill='toself', line_color='#ff4b4b'
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
        
        fig_bar = px.bar(df_barras, x='Média', y='Critério', orientation='h', text='Média', color='Média', color_continuous_scale='Reds')
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
            xaxis=dict(range=[0, 5.5], showgrid=False), yaxis=dict(title=""),
            coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=20)
        )
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    st.subheader("💬 Feedback Aberto da Equipe")
    if total_votos < 3 and nivel_logado != "ADMIN":
        st.warning("⚠️ **Confidencialidade:** Os comentários abertos só serão liberados para visualização do gestor após receberem pelo menos 3 avaliações, garantindo assim a segurança psicológica e o anonimato da equipe.")
    else:
        comentarios = df_notas['comentarios'].dropna().tolist()
        comentarios_validos = [c for c in comentarios if c.strip()]
        
        if not comentarios_validos:
            st.info("Nenhum comentário por escrito foi deixado neste ciclo.")
        else:
            for i, c in enumerate(comentarios_validos):
                st.markdown(f"<div style='background-color:#1e1e1e; padding:15px; border-radius:8px; margin-bottom:10px; border-left: 4px solid #ff4b4b;'><i>\"{c}\"</i></div>", unsafe_allow_html=True)

    registrar_auditoria("ACESSO DASHBOARD LIDERANÇA", f"Visualizou os resultados de {gestor_sel} ({ciclo_sel})", "N/A", nome_logado)