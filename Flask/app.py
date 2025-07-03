from flask import Flask, render_template, request, redirect, session
from flask_cors import CORS
from flask import url_for
from flask import make_response
import psycopg2

app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Variable global para control de intentos
attempts_left = 3

# --------------------------
# CONEXIÓN A LA BASE
# --------------------------
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="vyc",
        user="postgres",
        password="ubuntu"
    )

def obtener_datos_vista():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vista_usuarios_activos")
        datos = cursor.fetchall()
        cursor.close()
        conn.close()
        return datos
    except Exception as e:
        print(f"❌ Error al obtener datos de la vista: {e}")
        return []
    
def agregar_columna_estado():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS estado VARCHAR(10) DEFAULT 'activo';
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("Columna 'estado' agregada o ya existe.")
    except Exception as e:
        print(f"Error agregando columna estado: {e}")

def obtener_todos_usuarios():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""SELECT usuario_id, nombre, rol, estado FROM usuarios ORDER BY usuario_id
                      """)
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return usuarios
    except Exception as e:
        print(f"Error al obtener usuarios: {e}")
        return []
    
# --------------------------
# CREACIÓN DE TABLA (solo una vez)
# --------------------------
def crear_tabla_usuarios():

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario_id SERIAL PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL,
                contrasenia VARCHAR(50) NOT NULL,
                rol VARCHAR(20) NOT NULL DEFAULT 'usuario'),
                estado BOOLEAN NOT NULL DEFAULT TRUE
            """)

        conn.commit()
        print("✅ Tabla 'usuarios' verificada/creada correctamente.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al crear/verificar la tabla: {e}")

# --------------------------
# INSERTAR USUARIOS
# --------------------------    
def insertar_usuarios():
    usuarios = [
        ('MARCOS', 'OughTg', 'administrador'),
        ('MARIO', 'OrYEVE', 'administrador'),
        ('AITANA', 'LymERb', 'administrador'),
        ('BRAYAN', 'MonSYn', 'administrador'),
        ('ALEJANDRO', 'rTifoi', 'captura'),
        ('DAVID', 'ChemOU', 'captura'),
        ('ZAID', 'ChemOU', 'captura'),
        ('BRAULIO', 'ChemOU', 'captura'),
        ('OSCAR', 'ChemOU', 'captura')
    ]
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO usuarios (nombre, contrasenia, rol) VALUES (%s, %s, %s)",
            usuarios
        )
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Usuarios insertados correctamente.")
    except Exception as e:
        print(f"❌ Error al insertar usuarios: {e}")

# -----------------------------
# RUTA DE VALIDACION DE USUARIO
# -----------------------------
def validar_usuario(nombre, contrasenia):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT usuario_id, nombre, contrasenia, rol, estado 
            FROM usuarios 
            WHERE nombre = %s AND contrasenia = %s
        """, (nombre, contrasenia))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user  # Esto devuelve una tupla
    except Exception as e:
        print(f"Error en validación: {e}")
        return None


# --------------------------
# RUTA LOGIN
# --------------------------
@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    global attempts_left
    error = None

    if 'nombre' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        contrasenia = request.form['contrasenia']

        user = validar_usuario( nombre, contrasenia)

        if user:
            session['nombre'] = user[1]  # user[1] = nombre
            session['rol'] = user[3]      # user[3] = rol
            print(">> Sesión iniciada:", session)

            attempts_left = 3
            return redirect(url_for('dashboard'))
        else:
            attempts_left -= 1
            if attempts_left <= 0:
                error = "Has excedido el número de intentos."
            else:
                error = f"Usuario o contraseña incorrectos. Intentos restantes: {attempts_left}"

    return render_template('login.html', error=error)

# --------------------------
# VALIDACION DE CREACION DE USUARIOS
# en proceso
# --------------------------
@app.route('/registrar-usuario', methods=['GET', 'POST'])
def registrar_usuario():
    if 'usuario' not in session or session.get('rol') != 'administrador':
        return redirect(url_for('login'))

    mensaje = None

    if request.method == 'POST':
        nombre = request.form['nombre']
        contrasena = request.form['contrasena']
        rol = request.form['rol']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar si el usuario ya existe
            cursor.execute("SELECT * FROM usuarios WHERE nombre = %s", (nombre,))
            existente = cursor.fetchone()

            if existente:
                mensaje = "⚠️ Ya existe un usuario con ese nombre."
            else:
                # Insertar nuevo usuario
                cursor.execute(
                    "INSERT INTO usuarios (nombre, contrasenia, rol) VALUES (%s, %s, %s)",
                    (nombre, contrasena, rol)
                )
                conn.commit()
                mensaje = "✅ Usuario creado con éxito."

            cursor.close()
            conn.close()

        except Exception as e:
            mensaje = f"❌ Error al registrar usuario: {e}"

    return render_template('registrar_usuario.html', mensaje=mensaje)

# --------------------------
# RUTA DASHBOARD
# --------------------------

@app.route('/dashboard')
def dashboard():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    rol = session.get('rol')

    if rol == 'administrador':
        usuarios = obtener_todos_usuarios()  # Función que obtiene todos los usuarios
        response = make_response(
            render_template('dashboard.html',
                            nombre=session['nombre'],
                            rol=rol,
                            usuarios=usuarios)
        )
    else:
        # Si no es administrador, no se muestran usuarios
        response = make_response(
            render_template('dashboard.html',
                nombre=session['nombre'],
                rol=session['rol'],
                usuarios=usuarios)
        )

    # Evitar cache para forzar que se actualice la sesión
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# --------------------------
# RUTA CERRAR SESIÓN
# --------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --------------------------
# EJECUCIÓN PRINCIPAL
# --------------------------
if __name__ == '__main__':
    crear_tabla_usuarios()  # Se ejecuta solo una vez al iniciar
    agregar_columna_estado()
    usuarios = insertar_usuarios()
    for u  in usuarios:
        print(u)
    app.run(debug=True, port=5000)
