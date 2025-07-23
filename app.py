from flask import Flask, request, jsonify
import psycopg2
import os
import urllib.parse
from flask_cors import CORS  
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
#prompt para preguntarle a la IA
prompt = """quiero que busques en todas las paginas, documentos, portales, etc de la universidad nacional de colombia y filtres todo lo que son tramites estudiantiles (cambio de carrera, doble titulacion, etc) que se encuentren vigentes a la fecha, de todos los tramites que encuentres vas a extraer:

titulo del tramite

descripcion corta

enlace de donde lo sacaste

fecha de cierre del tramite (si es que tiene)

como respuesta me vas a dar UNICA Y EXCLUSIVAMENTE una linea de sql para ingresar esos datos a una tabla llamada tramites_prueba con nombres de columnas titulo,descripcion,enlace,date_cierre
Ahorrate cualquier otro tipo de contenido que no sea el código sql, tampoco pongas comillas, ni titulo sql antes, solo el codigo"""

app = Flask(__name__)
CORS(app)

# Configurar las credenciales
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
API_KEY = os.getenv("apikey")

#conectarse a la base de datos
def conectar_DB():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )

#funcion que sirve para limpiar la respuesta de la ia y dejarlo como un codigo ejecutable 
def limpiar_sql(texto):
    if texto.startswith("```sql"):
        texto = texto[6:]  # quitar ```sql\n
    if texto.endswith("```"):
        texto = texto[:-3]  # quitar ```
    return texto.strip()

#conexion con la DB y creacion del cursor de ejecución
conn = conectar_DB()
cur = conn.cursor()

#Actualización de los trámites con IA
def Actualizar_Tramites():
    
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        chat = model.start_chat(history=[])
        query = chat.send_message(prompt)
        cur.execute(limpiar_sql(query.text))
        conn.commit()
    except Exception as e:
        print(limpiar_sql(query.text))
        print("ocurrio un error",e)

Actualizar_Tramites()


def buscar_tramites(query):
    like = f"%{query}%"
    cur.execute("SELECT titulo,descripcion,enlace,date_cierre FROM tramites_prueba WHERE titulo ILIKE %s OR descripcion ILIKE %s", (like, like))
    resultados = cur.fetchall()
    cur.close()
    conn.close()
    return [{"titulo": t, "descripcion": d,"enlace": e, "date_cierre":dc } for t, d,e,dc in resultados]

@app.route("/api/tramites")
def tramites():
    q = request.args.get("q", "")
    return jsonify(buscar_tramites(q))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
