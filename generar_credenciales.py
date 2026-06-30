"""
Gestión de usuarios del sistema de liquidaciones JNT.
Ejecutar con: python generar_credenciales.py

Genera/actualiza config.yaml con las credenciales hasheadas.
Este archivo NO debe subirse a GitHub (está en .gitignore).
"""
import os
import yaml
import bcrypt

CONFIG_PATH = "config.yaml"


def cargar_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "credentials": {"usernames": {}},
        "cookie": {
            "expiry_days": 7,
            "key": "liquidaciones_jnt_secret_key_cambiar_esto",
            "name": "liquidaciones_jnt_auth",
        },
    }


def guardar_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    print(f"✓ config.yaml guardado.")


def hashear(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def agregar_usuario(config):
    print("\n--- AGREGAR USUARIO ---")
    username = input("Username (sin espacios, ej: glopez): ").strip().lower()
    if not username:
        print("Username no puede estar vacío.")
        return
    if username in config["credentials"]["usernames"]:
        print(f"El usuario '{username}' ya existe.")
        return
    name = input("Nombre completo: ").strip()
    email = input("Email: ").strip()
    password = input("Contraseña: ").strip()
    if not password:
        print("La contraseña no puede estar vacía.")
        return
    config["credentials"]["usernames"][username] = {
        "name": name,
        "email": email,
        "password": hashear(password),
    }
    guardar_config(config)
    print(f"✓ Usuario '{username}' ({name}) agregado.")


def cambiar_password(config):
    listar_usuarios(config)
    username = input("\nUsername al que cambiar contraseña: ").strip().lower()
    if username not in config["credentials"]["usernames"]:
        print(f"El usuario '{username}' no existe.")
        return
    password = input("Nueva contraseña: ").strip()
    if not password:
        print("La contraseña no puede estar vacía.")
        return
    config["credentials"]["usernames"][username]["password"] = hashear(password)
    guardar_config(config)
    print(f"✓ Contraseña de '{username}' actualizada.")


def listar_usuarios(config):
    usuarios = config["credentials"]["usernames"]
    if not usuarios:
        print("\nNo hay usuarios registrados.")
        return
    print("\n--- USUARIOS REGISTRADOS ---")
    for username, data in usuarios.items():
        print(f"  {username:15s}  {data.get('name', '-'):30s}  {data.get('email', '-')}")


def eliminar_usuario(config):
    listar_usuarios(config)
    username = input("\nUsername a eliminar: ").strip().lower()
    if username not in config["credentials"]["usernames"]:
        print(f"El usuario '{username}' no existe.")
        return
    confirmar = input(f"¿Confirmar eliminación de '{username}'? (s/n): ").strip().lower()
    if confirmar != "s":
        print("Cancelado.")
        return
    del config["credentials"]["usernames"][username]
    guardar_config(config)
    print(f"✓ Usuario '{username}' eliminado.")


if __name__ == "__main__":
    config = cargar_config()
    while True:
        print("\n=============================")
        print("  GESTIÓN DE USUARIOS - JNT  ")
        print("=============================")
        print("1. Agregar usuario")
        print("2. Listar usuarios")
        print("3. Cambiar contraseña")
        print("4. Eliminar usuario")
        print("5. Salir")
        opcion = input("Opción: ").strip()
        if opcion == "1":
            agregar_usuario(config)
        elif opcion == "2":
            listar_usuarios(config)
        elif opcion == "3":
            cambiar_password(config)
        elif opcion == "4":
            eliminar_usuario(config)
        elif opcion == "5":
            break
        else:
            print("Opción inválida.")
