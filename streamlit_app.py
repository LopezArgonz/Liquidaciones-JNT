import streamlit as st

st.set_page_config(
    page_title="Inicio - Liquidaciones JNT",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        height: 150px;
        font-size: 1.5rem;
        border-radius: 15px;
        border: 2px solid #e0e0e0;
        background-color: white;
        color: #2c3e50;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stButton>button:hover {
        border-color: #2c3e50;
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div style="text-align: center; margin-bottom: 3rem;">
        <h1 style="color: #2c3e50; font-size: 3rem;">⚖️ Sistema de Liquidación Laboral</h1>
        <h3 style="color: #555; font-weight: normal;">para la Justicia Nacional del Trabajo</h3>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")
st.write("### Seleccione una herramienta:")
st.write("")

col1, col2 = st.columns(2)

with col1:
    st.page_link("pages/1_Liquidacion_Despido.py", label="📄  Liquidación por Despido", use_container_width=True)

with col2:
    st.page_link("pages/2_Riesgos_Trabajo.py", label="🏥  Riesgos del Trabajo (Ley 24.557)", use_container_width=True)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.85rem; margin-top: 40px;'>"
    "Desarrollado por: <br><b>Gastón López Argonz</b>"
    "</div>", 
    unsafe_allow_html=True
)
