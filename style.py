import streamlit as st

def apply_custom_styles():
    """
    Aplica a identidade visual Premium Unificada: 
    - Fundo: Dark Coal #181818 com profundidade.
    - Destaques: Gradiente Laranja Vibrante.
    - Efeito: Glassmorphism e Profundidade 3D nos Cards.
    """
    st.markdown("""
        <style>
        /* 1. Importação de Fonte Moderna */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* 2. Fundo da Aplicação com Gradiente Suave */
        .stApp {
            background: radial-gradient(circle at top left, #1e1e1e 0%, #101010 100%) !important;
            background-attachment: fixed;
        }

        /* 3. Sidebar Estilizada (Glassmorphism) */
        [data-testid="stSidebar"] {
            background-color: rgba(18, 18, 18, 0.95) !important;
            border-right: 1px solid rgba(247, 122, 0, 0.3);
            backdrop-filter: blur(10px);
        }

        /* 4. Botões com Gradiente e Efeito de Brilho */
        div.stButton > button {
            background: linear-gradient(180deg, #f77a00 0%, #c36000 100%) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            font-size: 0.85rem;
            width: 100%;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        div.stButton > button:hover {
            transform: scale(1.02);
            box-shadow: 0px 8px 20px rgba(247, 122, 0, 0.4);
            border-color: rgba(255, 255, 255, 0.3) !important;
        }

        /* 5. TURBO NOS CARDS (st.metric) */
        [data-testid="stMetric"] {
            /* Fundo em gradiente para efeito 3D sutil */
            background: linear-gradient(145deg, #222222, #181818) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            
            /* Acento lateral laranja (Efeito de Dashboard Profissional) */
            border-left: 5px solid #f77a00 !important;
            
            padding: 20px !important;
            border-radius: 12px !important;
            
            /* Sombra projetada para profundidade */
            box-shadow: 8px 8px 16px #0c0c0c, -2px -2px 8px #242424 !important;
            transition: all 0.3s ease;
        }

        /* Microinteração ao passar o mouse no Card */
        [data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            border-left: 5px solid #ff9532 !important;
            box-shadow: 12px 12px 20px #080808, -2px -2px 12px #2a2a2a !important;
        }

        /* Texto do Rótulo (Label) */
        [data-testid="stMetricLabel"] {
            color: #aaaaaa !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
        }

        /* Valor Principal */
        [data-testid="stMetricValue"] {
            color: #f77a00 !important;
            font-weight: 800 !important;
            font-size: 2.2rem !important;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.4);
        }

        /* Estilização do Delta (Variação %) */
        [data-testid="stMetricDelta"] {
            background-color: rgba(0, 0, 0, 0.2) !important;
            padding: 2px 8px !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
        }

        /* 6. Inputs e Formulários */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
            background-color: #242424 !important;
            color: #e0e0e0 !important;
            border-radius: 8px !important;
            border: 1px solid #3d3d3d !important;
            transition: border-color 0.3s ease;
        }

        .stTextInput input:focus {
            border-color: #f77a00 !important;
            box-shadow: 0 0 0 1px #f77a00 !important;
        }

        /* 7. Melhoria em Tabelas e Dataframes */
        [data-testid="stDataFrame"] {
            border: 1px solid #333;
            border-radius: 10px;
            overflow: hidden;
        }

        /* 8. Estilo de Headers */
        h1, h2, h3 {
            letter-spacing: -0.5px;
            font-weight: 700 !important;
            color: white !important;
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #181818; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #f77a00; }
        </style>
    """, unsafe_allow_html=True)