import streamlit as st
from normas import NORMAS
from utils import (
    aplicar_estilos, aplicar_estilos_tabla, mostrar_footer,
    encabezado_institucional, chip_norma,
)

st.set_page_config(
    page_title="Biblioteca Legal - Liquidaciones JNT",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

aplicar_estilos()
aplicar_estilos_tabla()

AREA_LABELS = {"despido": "Liquidación por Despido", "lrt": "Riesgos del Trabajo"}


def main():
    encabezado_institucional(
        "Biblioteca de Leyes",
        "Legislación y jurisprudencia aplicable a las liquidaciones",
    )

    tab_legislacion, tab_jurisprudencia = st.tabs(["Legislación", "Jurisprudencia"])

    with tab_legislacion:
        filas_html = ""
        for n in NORMAS:
            enlace = chip_norma("Ver texto completo (InfoLEG)", n["url"])
            area = AREA_LABELS.get(n["area"], n["area"].title())
            filas_html += (
                f'<tr><td><b>{n["nombre"]}</b><br>'
                f'<span style="font-size:0.85rem;">{n["descripcion"]}</span></td>'
                f'<td style="white-space:nowrap;">{area}<br>{enlace}</td></tr>'
            )

        html = f"""
        <table class="table-jnt table-jnt-lista">
            <thead><tr><th>Norma</th><th>Aplica a / Enlace</th></tr></thead>
            <tbody>{filas_html}</tbody>
        </table>"""
        st.markdown(html, unsafe_allow_html=True)

    with tab_jurisprudencia:
        st.info("Próximamente: repositorio de fallos y jurisprudencia aplicable.")

    mostrar_footer()


if __name__ == "__main__":
    main()
