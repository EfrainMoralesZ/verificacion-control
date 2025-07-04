from flask import Flask, render_template, request, redirect, session, jsonify
from flask_cors import CORS
from flask import url_for
from flask import make_response
import psycopg2
import pandas as pd

app = Flask(__name__)
app.secret_key = 'clave_secreta'
df_clp = None # Funcion para leer lo excel

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
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios")
    usuarios = cur.fetchall()
    cur.close()
    conn.close()
    return usuarios
    
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
                contrasena VARCHAR(50) NOT NULL,
                rol VARCHAR(20) NOT NULL DEFAULT 'usuario',
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
        ('MARCOS', 'OughTg', 'Administrador'),
        ('MARIO', 'OrYEVE', 'Administrador'),
        ('AITANA', 'LymERb', 'Administrador'),
        ('BRAYAN', 'MonSYn', 'Administrador'),
        ('ALEJANDRO', 'rTifoi', 'Captura'),
        ('DAVID', 'ChemOU', 'Captura'),
        ('ZAID', 'tRosef', 'Captura'),
        ('BRAULIO', 'ZisenA', 'Captura'),
        ('OSCAR', 'NitRap', 'Captura')
    ]
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO usuarios (nombre, contrasena, rol) VALUES (%s, %s, %s)",
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
def validar_usuario(usuario, contrasena):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM usuarios WHERE nombre = %s AND contrasenia = %s",
        (usuario, contrasena)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user
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

    if 'usuario' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        user = validar_usuario(usuario, contrasena)

        if user:
            session['usuario'] = user[1]  # user[1] = usuario
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

    response = make_response(render_template('login.html', error=error))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
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
                    "INSERT INTO usuarios (nombre, contrasena, rol) VALUES (%s, %s, %s)",
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
    
    if 'usuario' not in session:
        return redirect(url_for('login'))

    rol = session.get('rol')
    usuario = session.get('usuario')

    usuarios = []  # Inicializa vacío por seguridad

    if rol == 'Administrador':
        usuarios = obtener_todos_usuarios()  # Solo si es administrador

    response = make_response(
        render_template('dashboard.html',
                        usuario=usuario,
                        rol=rol,
                        usuarios=usuarios)
    )

    # Evitar cache para que se actualice la sesión correctamente
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response

# --------------------------
# RUTA DECATHLON
# --------------------------
@app.route('/decathlon', methods=['GET', 'POST'])
def decathlon():
    global df_clp
    mensaje = None

    if request.method == 'POST':
        if 'clp_file' in request.files:
            archivo = request.files['clp_file']
            if archivo.filename.endswith('.xlsx') or archivo.filename.endswith('.xls'):
                df_clp = pd.read_excel(archivo)
                mensaje = "Archivo CLP cargado correctamente."
            else:
                mensaje = "Formato no válido. Solo archivos .xlsx o .xls."

    return render_template('decathlon.html', mensaje=mensaje)


@app.route('/validar_codigo', methods=['POST'])
def validar_codigo():
    global df_clp
    if df_clp is None:
        return jsonify({'resultado': '❌ Primero debes subir el archivo CLP.'})

    data = request.get_json()
    codigo = data.get('codigo')

    # Validar en columna A (índice 0) y obtener valor de columna F (índice 5)
    resultado = "❌ Código no encontrado."
    for _, row in df_clp.iterrows():
        if str(row[0]).strip() == codigo.strip():
            resultado = str(row[5]).strip()
            break

    return jsonify({'resultado': resultado})

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
