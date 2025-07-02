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
                rol VARCHAR(20) NOT NULL DEFAULT 'usuario');
            """)

        conn.commit()
        print("✅ Tabla 'usuarios' verificada/creada correctamente.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al crear/verificar la tabla: {e}")

# -----------------------------
# RUTA DE VALIDACION DE USUARIO
# -----------------------------
def validar_usuario(nombre, contrasenia):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta con nombres correctos de columnas
        cursor.execute(
            "SELECT * FROM usuarios WHERE nombre = %s AND contrasenia = %s",
            (nombre, contrasenia)
        )
        usuario = cursor.fetchone()

        cursor.close()
        conn.close()

        return usuario  # Si es None no existe
    except Exception as e:
        print(f"Error validando usuario: {e}")
        return None

# --------------------------
# RUTA LOGIN
# --------------------------
@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    global attempts_left

    # if 'usuario' in session:
    #     return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        user = validar_usuario(usuario, contrasena)  # ✅ usa tu función bien hecha

        if user:
            session['usuario'] = usuario
            attempts_left = 3
            return redirect(url_for('dashboard'))
        else:
            attempts_left -= 1
            error = f"Usuario o contraseña incorrectos. Intentos restantes: {attempts_left}"
            if attempts_left <= 0:
                error = "Has excedido el número de intentos."

    return render_template('login.html', error=error)

# --------------------------
# RUTA DASHBOARD
# --------------------------
@app.route('/dashboard')
def dashboard():
    if 'usuario' in session:
        return render_template('dashboard.html', usuario=session['usuario'])
    else:
        return redirect(url_for('login'))


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
    app.run(debug=True, port=5000)
