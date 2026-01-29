import streamlit as st
import pandas as pd
import altair as alt # Importante para os rótulos
from database import get_all_records_db

def render_relatorios():
    # --- CSS PARA IMPRESSÃO (Letras Pretas) ---
    st.markdown("""
        <style>
        @media print {
            body, .main, .stApp, h1, h2, h3, p, span, td, th {
                background-color: white !important;
                color: black !important;
            }
            header, [data-testid="stSidebar"], .stButton, [data-testid="stHeader"] {
                display: none !important;
            }
            * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📈 Relatórios de Performance")
    
    df_raw = get_all_records_db("monitorias")
    if df_raw is None or df_raw.empty:
        st.info("📊 Ainda não há dados registrados.")
        return

    # --- TRATAMENTO ---
    df = df_raw.copy()
    col_data = next((c for c in df.columns if c.lower() in ['criado_em', 'data', 'created_at']), None)
    df['nota'] = pd.to_numeric(df['nota'], errors='coerce').fillna(0)

    if col_data:
        df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
        df = df.dropna(subset=[col_data])
        df['data_filtro'] = df[col_data].dt.date
    else:
        st.error("Coluna de data não encontrada.")
        return

    # --- FILTROS ---
    c1, c2 = st.columns(2)
    with c1:
        min_d, max_d = df['data_filtro'].min(), df['data_filtro'].max()
        periodo = st.date_input("Filtrar Período", [min_d, max_d], key="label_f_date")
    with c2:
        lista_sdrs = ["Todos"] + sorted(df['sdr'].unique().tolist())
        sdr_sel = st.selectbox("Filtrar SDR", lista_sdrs, key="label_f_sdr")

    # Filtragem
    df_f = df.copy()
    if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
        df_f = df_f[(df_f['data_filtro'] >= periodo[0]) & (df_f['data_filtro'] <= periodo[1])]
    if sdr_sel != "Todos":
        df_f = df_f[df_f['sdr'] == sdr_sel]

    # --- GRÁFICOS COM RÓTULOS ---
    if not df_f.empty:
        st.subheader("📊 Volume de Monitorias por SDR")
        df_f['Nome'] = df_f['sdr'].apply(lambda x: str(x).split()[0])
        
        # Prepara dados para o gráfico de volume
        df_vol = df_f.groupby('Nome').size().reset_index(name='Quantidade')
        
        # Criação do gráfico Altair com Rótulos 
        bars = alt.Chart(df_vol).mark_bar(color='#1f77b4').encode(
            x=alt.X('Nome:N', title='SDR'),
            y=alt.Y('Quantidade:Q', title='Qtd Monitorias')
        )

        text = bars.mark_text(
            align='center',
            baseline='bottom',
            dy=-5, # Afasta o texto para cima da barra
            color='black' if st.get_option("theme.base") == "light" else "white"
        ).encode(
            text='Quantidade:Q'
        )

        st.altair_chart(bars + text, use_container_width=True)
        
        # Gráfico de Médias (Simples)
        st.subheader("📉 Média de Notas")
        chart_media = df_f.groupby('Nome')['nota'].mean()
        st.line_chart(chart_media)
    else:
        st.warning("Sem dados para os filtros selecionados.")

    st.divider()

    # --- TABELA FINAL ---
    st.subheader("📋 Últimas 10 Monitorias")
    dados_tabela = df_f if not df_f.empty else df.head(10)
    dados_tabela = dados_tabela.copy()
    dados_tabela['Data_Formatada'] = dados_tabela[col_data].dt.strftime('%d/%m/%Y')
    
    cols_view = ['Data_Formatada', 'sdr', 'nota', 'monitor_responsavel']
    exibir = [c for c in cols_view if c in dados_tabela.columns]
    
    st.table(dados_tabela.sort_values(by=col_data, ascending=False)[exibir].head(10))