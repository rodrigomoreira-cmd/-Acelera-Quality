import streamlit as st

def apply_custom_styles():
    """
    Aplica a identidade visual: 
    Fundo: Gradiente entre dois tons de preto (#000000 e #0e1117)
    Botões: Gradiente Laranja (#f77a00 para #c36000)
    """
    st.markdown(f"""
        <style>
        /* 1. Fundo da Aplicação (Dois tons de preto de cima para baixo) */
        .stApp {{
            background: linear-gradient(180deg, #000000 0%, #0e1117 100%) !important;
            background-attachment: fixed;
        }}

        /* 2. Barra Lateral (Sidebar) em preto sólido para contraste */
        [data-testid="stSidebar"] {{
            background-color: #000000 !important;
            border-right: 1px solid #f77a00;
        }}

        /* 3. Estilização dos Botões (Gradiente Laranja Profissional) */
        div.stButton > button {{
            background: linear-gradient(180deg, #f77a00 0%, #c36000 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            font-weight: 700;
            width: 100%;
            transition: all 0.3s ease;
        }}
        
        div.stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0px 5px 15px rgba(247, 122, 0, 0.4);
        }}

        /* 4. Cores de Texto e Métricas (Branco e Laranja) */
        h1, h2, h3, p, span, label, [data-testid="stMetricLabel"] {{
            color: #FFFFFF !important;
        }}
        
        [data-testid="stMetricValue"] {{
            color: #f77a00 !important;
        }}

        /* 5. Inputs, Seletores e Tabelas */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: #1a1a1a !important;
            color: white !important;
            border: 1px solid #333333 !important;
        }}

        /* Estilo para Dataframes (Tabelas) ficarem escuras */
        [data-testid="stDataFrame"] {{
            background-color: #000000 !important;
        }}
        </style>
    """, unsafe_allow_html=True)