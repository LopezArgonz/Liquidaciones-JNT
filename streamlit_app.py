import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

st.set_page_config(
    page_title="Inicio - Liquidaciones JNT",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Cargar credenciales
try:
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.load(f, Loader=SafeLoader)
except FileNotFoundError:
    st.error("Archivo de configuración no encontrado. Ejecute `generar_credenciales.py` para crear los usuarios.")
    st.stop()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

authenticator.login()

if st.session_state.get("authentication_status") is True:

    p_despido = st.Page("pages/1_Liquidacion_Despido.py", title="Liquidación por Despido", icon="📄")
    p_lrt     = st.Page("pages/2_Riesgos_Trabajo.py",    title="Riesgos del Trabajo (Ley 24.557)", icon="🏥")

    def pagina_inicio():
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
            if st.button("📄\nLiquidación por Despido", use_container_width=True):
                st.switch_page(p_despido)

        with col2:
            if st.button("🏥\nRiesgos del Trabajo (Ley 24.557)", use_container_width=True):
                st.switch_page(p_lrt)

        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #888; font-size: 0.85rem; margin-top: 40px;'>"
            "Desarrollado por: <br><b>Gastón López Argonz</b>"
            "</div>",
            unsafe_allow_html=True
        )

    with st.sidebar:
        st.markdown(f"👤 **{st.session_state['name']}**")
        authenticator.logout("Cerrar sesión")
        st.markdown("---")

    p_inicio = st.Page(pagina_inicio, title="Inicio", default=True)
    pg = st.navigation([p_inicio, p_despido, p_lrt], position="hidden")
    pg.run()

elif st.session_state.get("authentication_status") is False:
    st.error("Usuario o contraseña incorrectos.")
