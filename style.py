import streamlit as st

def apply_custom_styles():
    """
    Aplica a identidade visual: 
    Fundo: Gradiente #6a6b77 para #2b2a2f
    Botões: Gradiente #f77a00 para #c36000
    """
    st.markdown(f"""
        <style>
        /* 1. Fundo da Aplicação (Gradiente de cima para baixo) */
        .stApp {{
            background: linear-gradient(180deg, #6a6b77 0%, #2b2a2f 100%) !important;
            background-attachment: fixed;
        }}

        /* 2. Barra Lateral (Sidebar) */
        [data-testid="stSidebar"] {{
            background-color: #2b2a2f !important;
            border-right: 1px solid #f77a00;
        }}

        /* 3. Estilização de todos os Botões (Gradiente Laranja) */
        div.stButton > button {{
            background: linear-gradient(180deg, #f77a00 0%, #c36000 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            font-weight: 700;
            transition: transform 0.2s;
            width: 100%;
        }}
        
        div.stButton > button:hover {{
            transform: scale(1.02);
            box-shadow: 0px 4px 15px rgba(247, 122, 0, 0.4);
        }}

        /* 4. Cores de Texto e Métricas */
        h1, h2, h3, p, span, label, [data-testid="stMetricLabel"] {{
            color: white !important;
        }}
        
        /* Força o valor da métrica a ficar visível */
        [data-testid="stMetricValue"] {{
            color: #f77a00 !important;
        }}

        /* 5. Inputs e Áreas de Texto */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border: 1px solid #6a6b77 !important;
        }}
        </style>
    """, unsafe_allow_html=True)