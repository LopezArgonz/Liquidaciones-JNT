import streamlit as st
import yaml
from yaml.loader import SafeLoader
from datetime import datetime
import streamlit_authenticator as stauth
from app_liquidacion import obtener_datos_online, cargar_ipc_seed
from app_lrt import cargar_ripte_seed
from utils import (
    aplicar_estilos, mostrar_footer, alerta, encabezado_institucional,
    icono_balanza, icono_toga, icono_columna, icono_cruz, icono_libro,
)

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
    alerta("Error de configuración del sistema. Contacte al administrador.")
    st.stop()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)


@st.cache_data(ttl=3600)
def _estado_indices():
    """Última fecha IPC disponible y último período RIPTE del seed (falla en silencio sin red)."""
    ipc_fecha = None
    try:
        _, ipc_fecha = obtener_datos_online()
    except Exception:
        pass
    if not ipc_fecha:
        try:
            seed_ipc = cargar_ipc_seed()
            ipc_fecha = datetime.strptime(max(seed_ipc.keys()), "%Y-%m-%d").strftime("%m/%Y")
        except Exception:
            ipc_fecha = "N/D"

    try:
        seed_ripte = cargar_ripte_seed()
        ripte_fecha = datetime.strptime(max(seed_ripte.keys()), "%Y-%m-%d").strftime("%m/%Y")
    except Exception:
        ripte_fecha = "N/D"

    return ipc_fecha, ripte_fecha


def _tarjeta_herramienta(etiqueta, icono_svg, titulo, descripcion, page):
    st.markdown(f"""
        <div class="jnt-tarjeta-herr">
            <div class="jnt-tarjeta-etiqueta">{etiqueta}</div>
            <div class="jnt-tarjeta-icono">{icono_svg}</div>
            <div class="jnt-tarjeta-titulo">{titulo}</div>
            <div class="jnt-tarjeta-desc">{descripcion}</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button(f"Ingresar — {titulo}", key=f"btn_{titulo}", use_container_width=True):
        st.switch_page(page)


# Placeholder reserva el espacio visual arriba del formulario de login
branding_placeholder = st.empty()

authenticator.login()

if st.session_state.get("authentication_status") is True:
    branding_placeholder.empty()

    p_despido    = st.Page("pages/1_Liquidacion_Despido.py", title="Liquidación por Despido")
    p_lrt        = st.Page("pages/2_Riesgos_Trabajo.py",    title="Riesgos del Trabajo (Ley 24.557)")
    p_biblioteca = st.Page("pages/3_Biblioteca_Legal.py",   title="Biblioteca de Leyes")

    def pagina_inicio():
        aplicar_estilos()
        encabezado_institucional("Sistema de Liquidación Laboral", "Justicia Nacional del Trabajo")

        nombre = st.session_state.get("name", "")
        st.markdown(
            f"<p style='color:var(--jnt-azul-claro,#2C3E50); font-size:1.05rem;'>"
            f"Bienvenido/a, Dr./Dra. <b>{nombre}</b></p>",
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            _tarjeta_herramienta(
                "LCT — DESPIDO", icono_columna(40), "Liquidación por Despido",
                "Indemnizaciones, preaviso, SAC, multas y actualización IPC INDEC + 3% anual.",
                p_despido,
            )
        with col2:
            _tarjeta_herramienta(
                "LRT — LEY 24.557", icono_cruz(40), "Riesgos del Trabajo",
                "Prestación dineraria por incapacidad permanente parcial, actualizada por RIPTE.",
                p_lrt,
            )
        with col3:
            _tarjeta_herramienta(
                "BIBLIOTECA", icono_libro(40), "Biblioteca de Leyes",
                "Legislación aplicable con enlace a InfoLEG (próximamente, jurisprudencia).",
                p_biblioteca,
            )

        st.markdown("---")
        ipc_fecha, ripte_fecha = _estado_indices()
        st.markdown(
            f"<div style='text-align:center; font-size:0.78rem; color:var(--jnt-azul-claro,#2C3E50);'>"
            f"Último IPC INDEC disponible: <b>{ipc_fecha}</b> &nbsp;&middot;&nbsp; "
            f"Último período RIPTE (seed): <b>{ripte_fecha}</b></div>",
            unsafe_allow_html=True,
        )

        mostrar_footer()

    with st.sidebar:
        st.markdown(
            f"<div style='display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;'>"
            f"{icono_toga(20)}<b>{st.session_state['name']}</b></div>",
            unsafe_allow_html=True,
        )
        authenticator.logout("Cerrar sesión")
        st.markdown("---")

        col_i1, col_i2 = st.columns([1, 6])
        with col_i1:
            st.markdown(icono_columna(18), unsafe_allow_html=True)
        with col_i2:
            st.page_link(p_despido, label="Liquidación por Despido")

        col_i1, col_i2 = st.columns([1, 6])
        with col_i1:
            st.markdown(icono_cruz(18), unsafe_allow_html=True)
        with col_i2:
            st.page_link(p_lrt, label="Riesgos del Trabajo")

        col_i1, col_i2 = st.columns([1, 6])
        with col_i1:
            st.markdown(icono_libro(18), unsafe_allow_html=True)
        with col_i2:
            st.page_link(p_biblioteca, label="Biblioteca de Leyes")

        st.markdown("---")

    p_inicio = st.Page(pagina_inicio, title="Inicio", default=True)
    pg = st.navigation([p_inicio, p_despido, p_lrt, p_biblioteca], position="hidden")
    pg.run()

else:
    with branding_placeholder.container():
        st.markdown(f"""
            <div class="jnt-login-card">
                <div class="jnt-login-icono">{icono_balanza(64)}</div>
                <h1 class="jnt-login-titulo">Sistema de Liquidación Laboral</h1>
                <div class="jnt-login-leyenda">Justicia Nacional del Trabajo</div>
            </div>
        """, unsafe_allow_html=True)
    if st.session_state.get("authentication_status") is False:
        alerta("Usuario o contraseña incorrectos. Si olvidó sus credenciales, contacte al administrador.")
