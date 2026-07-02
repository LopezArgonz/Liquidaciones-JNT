import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from utils import aplicar_estilos, mostrar_footer

st.set_page_config(
    page_title="Inicio - Liquidaciones JNT",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="auto"
)

aplicar_estilos()

# Cargar credenciales
try:
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.load(f, Loader=SafeLoader)
except FileNotFoundError:
    st.error("Error de configuración del sistema. Contacte al administrador.")
    st.stop()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# Placeholder reserva el espacio visual arriba del formulario de login
branding_placeholder = st.empty()

authenticator.login()

if st.session_state.get("authentication_status") is True:
    branding_placeholder.empty()

    p_despido = st.Page("pages/1_Liquidacion_Despido.py", title="Liquidación por Despido", icon="📄")
    p_lrt     = st.Page("pages/2_Riesgos_Trabajo.py",    title="Riesgos del Trabajo (Ley 24.557)", icon="🏥")

    def pagina_inicio():
        aplicar_estilos()
        st.markdown("""
            <style>
            .stButton>button {
                height: 150px;
                font-size: 1.5rem;
                border-radius: 15px;
                border: 2px solid #e0e0e0;
                background-color: white;
                color: #2c3e50;
            }
            </style>
        """, unsafe_allow_html=True)

        nombre = st.session_state.get("name", "")
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 3rem;">
                <h1 style="color: #2c3e50; font-size: 3rem;">⚖️ Sistema de Liquidación Laboral</h1>
                <h3 style="color: #555; font-weight: normal;">para la Justicia Nacional del Trabajo</h3>
                <p style="color: #888; margin-top: 0.5rem;">Bienvenido/a, <b>{nombre}</b></p>
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
        mostrar_footer()

    with st.sidebar:
        st.markdown(f"👤 **{st.session_state['name']}**")
        authenticator.logout("Cerrar sesión")
        st.markdown("---")

    p_inicio = st.Page(pagina_inicio, title="Inicio", default=True)
    pg = st.navigation([p_inicio, p_despido, p_lrt], position="hidden")
    pg.run()

else:
    with branding_placeholder.container():
        st.markdown("""
            <div style="text-align: center; margin-bottom: 2rem; margin-top: 3rem;">
                <h1 style="color: #2c3e50; font-size: 2.5rem;">⚖️ Sistema de Liquidación Laboral</h1>
                <h4 style="color: #555; font-weight: normal;">Justicia Nacional del Trabajo</h4>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
    if st.session_state.get("authentication_status") is False:
        st.error("Usuario o contraseña incorrectos. Si olvidó sus credenciales, contacte al administrador.")
