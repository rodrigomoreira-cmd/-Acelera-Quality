import streamlit as st

def apply_custom_styles():
    """
    Aplica a identidade visual: 
    Fundo: Preto sólido #181818 (com leve gradiente para profundidade)
    Botões: Gradiente Laranja de cima para baixo
    """
    st.markdown(f"""
        <style>
        /* 1. Fundo da Aplicação (Cor #181818 conforme solicitado) */
        .stApp {{
            background: linear-gradient(180deg, #181818 0%, #101010 100%) !important;
            background-attachment: fixed;
        }}

        /* 2. Barra Lateral (Sidebar) em harmonia com o fundo */
        [data-testid="stSidebar"] {{
            background-color: #121212 !important;
            border-right: 1px solid #f77a00;
        }}

        /* 3. Estilização dos Botões (Gradiente Laranja #f77a00 para #c36000) */
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

        /* 4. Cores de Texto e Métricas */
        h1, h2, h3, p, span, label, [data-testid="stMetricLabel"] {{
            color: #FFFFFF !important;
        }}
        
        [data-testid="stMetricValue"] {{
            color: #f77a00 !important;
        }}

        /* 5. Inputs e Campos de Seleção com fundo levemente mais claro para contraste */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: #242424 !important;
            color: white !important;
            border: 1px solid #333333 !important;
        }}

        /* Tabelas (Dataframes) */
        [data-testid="stDataFrame"] {{
            background-color: #181818 !important;
        }}
        </style>
    """, unsafe_allow_html=True)