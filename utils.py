import streamlit as st

CSS_BASE = """
<style>
.main {
    background-color: #f8f9fa;
}
h1 {
    color: #2c3e50;
}
.stButton>button {
    background-color: #2c3e50;
    color: white;
    border-radius: 8px;
    width: 100%;
    border: none;
    padding: 0.5rem 1rem;
    font-weight: 500;
    transition: all 0.3s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.stButton>button:hover {
    background-color: #34495e;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    transform: translateY(-1px);
}
.stButton>button:active {
    transform: translateY(0px);
}
</style>
"""

CSS_TABLA = """
<style>
.table-jnt {
    width: 100% !important;
    border-collapse: collapse !important;
    font-family: sans-serif;
    font-size: 0.9rem;
    color: inherit !important;
}
.table-jnt thead tr th {
    text-align: center !important;
    background-color: rgba(128, 128, 128, 0.15);
    padding: 10px;
    border-bottom: 2px solid rgba(128, 128, 128, 0.3);
    color: inherit !important;
}
.table-jnt tbody tr td {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    color: inherit !important;
}
.table-jnt tbody tr td:nth-child(2) {
    text-align: right !important;
    white-space: nowrap;
}
.table-jnt tbody tr:last-child {
    font-weight: bold;
    background-color: rgba(128, 128, 128, 0.1);
    border-top: 2px solid rgba(128, 128, 128, 0.3);
}
.table-jnt tr.separador td {
    border-top: 2px solid rgba(44, 62, 80, 0.3);
    font-weight: bold;
    background-color: rgba(44, 62, 80, 0.05);
}
</style>
"""


def aplicar_estilos():
    st.markdown(CSS_BASE, unsafe_allow_html=True)


def aplicar_estilos_tabla():
    st.markdown(CSS_TABLA, unsafe_allow_html=True)


def mostrar_footer():
    st.markdown(
        "<div style='text-align: center; color: #888; font-size: 0.85rem; margin-top: 20px;'>"
        "Desarrollado por: <br><b>Gastón López Argonz</b>"
        "</div>",
        unsafe_allow_html=True,
    )
