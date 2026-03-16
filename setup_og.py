import streamlit
from pathlib import Path

st_html_path = Path(streamlit.__file__).parent / "static" / "index.html"
with open(st_html_path, "r", encoding="utf-8") as f:
    html = f.read()

og_tags = """
<title>Liquidaciones JNT</title>
<meta property="og:title" content="Liquidaciones JNT">
<meta property="og:description" content="Sistema de Liquidación Laboral para la Justicia Nacional del Trabajo">
<meta property="og:image" content="https://raw.githubusercontent.com/LopezArgonz/Liquidaciones-JNT/main/logo.png">
<meta property="og:url" content="https://liquidacionesjnt.nbdigital.lat/">
<meta name="twitter:card" content="summary_large_image">
"""

html_modified = False

if "<title>Streamlit</title>" in html:
    html = html.replace("<title>Streamlit</title>", "")
    html_modified = True

if 'property="og:title"' not in html:
    html = html.replace("<head>", f"<head>\n{og_tags}")
    html_modified = True

if html_modified:
    with open(st_html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Etiquetas OpenGraph inyectadas y título actualizado correctamente en index.html")
else:
    print("✅ Las etiquetas OpenGraph y el título ya estaban configurados en index.html")
