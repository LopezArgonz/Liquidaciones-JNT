import streamlit
import os

# Buscamos el archivo index.html real dentro de la librería instalada
st_dir = os.path.dirname(streamlit.__file__)
index_path = os.path.join(st_dir, "static", "index.html")

with open(index_path, "r", encoding="utf-8") as f:
    content = f.read()

# Definimos las etiquetas OpenGraph y el Título
# Usamos el logo directamente desde el repo de GitHub para que los scrapers lo encuentren fácil
og_tags = """
    <title>Liquidaciones JNT</title>
    <meta property="og:title" content="Liquidaciones JNT" />
    <meta property="og:type" content="website" />
    <meta property="og:description" content="Sistema de Liquidación Laboral para la Justicia Nacional del Trabajo" />
    <meta property="og:image" content="https://raw.githubusercontent.com/LopezArgonz/Liquidaciones-JNT/main/logo.png" />
    <meta property="og:url" content="https://liquidacionesjnt.nbdigital.lat/" />
    <meta name="twitter:card" content="summary_large_image" />
"""

# Eliminamos cualquier etiqueta <title> preexistente de Streamlit para que no haya duplicados
import re
content = re.sub(r'<title>.*?</title>', '', content)

# Inyectamos nuestras etiquetas justo después de la apertura de <head>
if "<head>" in content:
    content = content.replace("<head>", f"<head>{og_tags}")

with open(index_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ index.html de Streamlit parcheado con éxito!")
