import streamlit
from pathlib import Path

st_html_path = Path(streamlit.__file__).parent / "static" / "index.html"
with open(st_html_path, "r", encoding="utf-8") as f:
    html = f.read()

og_tags = """
<meta property="og:title" content="Liquidador Laboral - JNT">
<meta property="og:description" content="Sistema de Liquidación Laboral para la Justicia Nacional del Trabajo">
<meta property="og:image" content="https://raw.githubusercontent.com/LopezArgonz/Liquidaciones-JNT/main/logo.png">
<meta property="og:url" content="https://liquidacionesjnt.nbdigital.lat/">
<meta name="twitter:card" content="summary_large_image">
"""

if 'property="og:title"' not in html:
    html = html.replace("<head>", f"<head>\n{og_tags}")
    with open(st_html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Etiquetas OpenGraph inyectadas correctamente en index.html de Streamlit")
else:
    print("✅ Las etiquetas OpenGraph ya existen en index.html")
