from flask import Flask, render_template, request, redirect, session
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

# --------------------------
# RUTA LOGIN
# --------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    global attempts_left
    error = None

    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        contrasena = request.form['contrasena'].strip()

        if not usuario or not contrasena:
            error = "Ingrese usuario y contrasenia."
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                query = "SELECT rol FROM usuarios WHERE nombre = %s AND contrasenia = %s"
                cursor.execute(query, (usuario, contrasena))
                result = cursor.fetchone()

                cursor.close()
                conn.close()

                if result:
                    rol = result[0]
                    session['usuario'] = usuario
                    session['rol'] = rol
                    attempts_left = 3  # reset
                    return f"Bienvenido {usuario}, tu rol es {rol}"
                else:
                    attempts_left -= 1
                    if attempts_left > 0:
                        error = f"Usuario o contrasenia incorrectos. Intentos restantes: {attempts_left}"
                    else:
                        error = "Demasiados intentos fallidos. Reinicie el navegador."
            except Exception as e:
                error = f"Error al conectar con la base de datos: {str(e)}"

    return render_template('Login.html', error=error)

# --------------------------
# EJECUCIÓN PRINCIPAL
# --------------------------
if __name__ == '__main__':
    crear_tabla_usuarios()  # Se ejecuta solo una vez al iniciar
    app.run(debug=True, port=5000)
