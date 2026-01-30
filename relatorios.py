import streamlit as st
import pandas as pd
from database import get_all_records_db

def render_relatorios():
    # Segurança: Apenas ADMIN deve acessar relatórios brutos
    if st.session_state.get('nivel') != "ADMIN":
        st.error("Acesso restrito a administradores.")
        return

    st.title("📈 Relatórios e Exportação")
    st.markdown("Extraia os dados completos das monitorias para análises externas.")
    
    # 1. BUSCA DADOS DO BANCO
    df = get_all_records_db("monitorias")
    
    if df is not None and not df.empty:
        # Tratamento de dados
        df['criado_em'] = pd.to_datetime(df['criado_em'])
        df['nota'] = pd.to_numeric(df['nota'], errors='coerce')
        
        # --- FILTROS ---
        with st.container(border=True):
            st.subheader("🔍 Filtrar Dados")
            col1, col2 = st.columns(2)
            
            with col1:
                lista_sdr = ["Todos"] + sorted(df['sdr'].unique().tolist())
                sdr_selecionado = st.selectbox("Selecione o SDR", lista_sdr)
                
            with col2:
                df['mes_ano'] = df['criado_em'].dt.strftime('%m/%Y')
                lista_meses = ["Todos"] + sorted(df['mes_ano'].unique().tolist(), reverse=True)
                mes_selecionado = st.selectbox("Selecione o Mês", lista_meses)

        # Aplicando os filtros
        df_filtrado = df.copy()
        if sdr_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['sdr'] == sdr_selecionado]
        if mes_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['mes_ano'] == mes_selecionado]

        # --- MÉTRICAS DO PERÍODO FILTRADO ---
        if not df_filtrado.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Qtd. Monitorias", len(df_filtrado))
            m2.metric("Média Qualidade", f"{df_filtrado['nota'].mean():.1f}%")
            m3.metric("Maior Nota", f"{df_filtrado['nota'].max():.1f}%")

            # --- EXIBIÇÃO ---
            st.divider()
            st.dataframe(
                df_filtrado.drop(columns=['mes_ano']), 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "nota": st.column_config.NumberColumn("Nota (%)", format="%.1f%%"),
                    "criado_em": st.column_config.DatetimeColumn("Data/Hora", format="DD/MM/YYYY HH:mm")
                }
            )

            # --- EXPORTAÇÃO CSV ---
            st.subheader("📥 Exportar")
            
            # Preparação do arquivo para Excel (utf-8-sig e ponto-e-vírgula)
            csv_data = df_filtrado.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')

            st.download_button(
                label="📄 Baixar Relatório em CSV (Excel)",
                data=csv_data,
                file_name=f"relatorio_monitorias_{sdr_selecionado.replace(' ', '_').lower()}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
            st.caption("💡 O arquivo está configurado para abrir direto no Excel sem necessidade de importar dados.")
        else:
            st.warning("Nenhum registro encontrado para os filtros selecionados.")

    else:
        st.info("💡 Não há dados de monitoria registrados para gerar relatórios.")