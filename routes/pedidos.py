from flask import Blueprint, render_template, request, redirect, session
import pandas as pd
import os
import uuid
from datetime import datetime
from services.catalogo import cargar_catalogo

pedidos_bp = Blueprint("pedidos", __name__)

#@pedidos_bp.route("/")
#def index():
 #   return render_template("index.html")

@pedidos_bp.route("/")
def inicio():
    return render_template("inicio.html")

@pedidos_bp.route("/ver_pedidos")
def ver_pedidos():
    ruta_archivo = os.path.join("data", "pedidos.csv")

    try:
        df = pd.read_csv(ruta_archivo, sep=";", encoding="latin1")
        pedidos = df.to_dict(orient="records")
    except FileNotFoundError:
        pedidos = []

    return render_template("ver_pedidos.html", pedidos=pedidos)
@pedidos_bp.route("/catalogo")
def catalogo():
    return render_template("catalogo.html")




# Ruta: /cargar_manual
@pedidos_bp.route("/cargar_manual", methods=["GET"])
def mostrar_formulario_manual():
    return render_template("cargar_manual.html")
@pedidos_bp.route("/cargar_manual", methods=["POST"])
def cargar_manual():
    DATA_FILE = os.path.join("data", "pedidos.csv")

    data = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    catalogo = cargar_catalogo()

    servicio = request.form["servicio"]
    dietas_seleccionadas = request.form.getlist("dieta")
    otra_dieta = request.form.get("otra_dieta", "").strip()

    if "Otra" in dietas_seleccionadas and otra_dieta:
        dietas_seleccionadas.remove("Otra")
        dietas_seleccionadas.append(f"Otra: {otra_dieta}")

    cantidad = int(request.form["cantidad"])
    precio_total = 0

    for dieta in dietas_seleccionadas:
        match = catalogo[(catalogo["Servicio"] == servicio) & (catalogo["Dieta"] == dieta)]
        if not match.empty:
            precio_total += match["Precio"].values[0]

    valor_total = cantidad * precio_total
    dietas_txt = ", ".join(dietas_seleccionadas)

    pedido = {
        "ID Pedido": str(uuid.uuid4())[:8],
        "Fecha Solicitud": request.form["fecha_solicitud"],
        "Fecha Entrega": request.form["fecha_entrega"],
        "Hora Entrega Real": request.form["hora_entrega"],
        "Hora Recogida Menaje": request.form["hora_recogida"],
        "Cama": request.form["cama"],
        "Servicio": servicio,
        "Dietas": dietas_txt,
        "Cantidad": cantidad,
        "Precio Unitario Total": precio_total,
        "Valor Total": valor_total,
        "Estado Entrega": "Entregado" if request.form.get("estado_entrega") else "Pendiente",
        "Estado Recogida": "Recogido" if request.form.get("estado_recogida") else "Pendiente",
        "Tiempo Servicio (min)": calcular_tiempo(request.form["hora_entrega"], request.form["hora_recogida"]),
        "Condición Menaje": request.form["condicion_menaje"],
        "Observaciones Menaje": request.form["observaciones_menaje"],
        "Firmado por Enfermería": "Sí" if request.form.get("firmado") else "No"
    }

    data.loc[len(data)] = pedido
    data.to_csv(DATA_FILE, index=False, sep=";", encoding="latin1")

    return redirect("/ver_pedidos")


# Utilidad: calcular diferencia de tiempo
def calcular_tiempo(hora1, hora2):
    try:
        fmt = "%H:%M"
        h1 = datetime.strptime(hora1, fmt)
        h2 = datetime.strptime(hora2, fmt)
        return int((h2 - h1).total_seconds() // 60)
    except:
        return ""
from werkzeug.utils import secure_filename
from services.catalogo import cargar_catalogo
from services.utils import normalizar
from time import time

@pedidos_bp.route("/cargar_censo", methods=["GET", "POST"])
def cargar_censo():
    if request.method == "GET":
        return render_template("cargar_censo.html")

    archivo = request.files["archivo"]
    if not archivo:
        return "No se ha seleccionado ningún archivo", 400

    filename = secure_filename(archivo.filename)
    extension = filename.split(".")[-1].lower()
    nombre_archivo = filename.lower()

    if "almuerzo" in nombre_archivo:
        servicio_detectado = "Almuerzo"
    elif "cena" in nombre_archivo:
        servicio_detectado = "Cena"
    else:
        servicio_detectado = "Desayuno"  # Por defecto

    if extension in ["xls", "xlsx"]:
        df = pd.read_excel(archivo, engine="openpyxl")
    else:
        return "Tipo de archivo no soportado. Usa un archivo Excel (.xlsx o .xls)", 400

    print("Contenido leído del archivo:")
    print(df.head(10))

    df.columns = [col.upper().strip()
                  .replace("Á", "A").replace("É", "E")
                  .replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
                  for col in df.columns]
    print("Columnas del censo:", df.columns.tolist())

    columnas_requeridas = {"ID", "PACIENTE", "PABELLON", "CAMA", "AISLADO", "DIETA", "OBSERVACIONES"}
    if not columnas_requeridas.issubset(set(df.columns)):
        return f"El archivo no contiene todas las columnas requeridas. Columnas encontradas: {df.columns.tolist()}", 400

    DATA_FILE = os.path.join("data", "pedidos.csv")
    try:
        df_pedidos = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
        df_pedidos = df_pedidos.loc[:, ~df_pedidos.columns.str.contains("Unnamed|,")]
        df_pedidos = df_pedidos.rename(columns={
            "CondiciÃ³n Menaje": "Condición Menaje",
            "Firmado por EnfermerÃ­a": "Firmado por Enfermería",
            "PabellÃ³n": "Pabellón"
        })
        df_pedidos = df_pedidos.loc[:, ~df_pedidos.columns.duplicated()]
    except FileNotFoundError:
        df_pedidos = pd.DataFrame()

    hoy = datetime.now().strftime("%Y-%m-%d")
    cds = session.get("cds", "NO_CDS")
    nuevos_pedidos = []

    inicio = time()

    catalogo = cargar_catalogo()
    catalogo["Dieta_Normalizada"] = catalogo["Dieta"].apply(normalizar)

    for index, fila in df.iterrows():
        try:
            aislado = str(fila["AISLADO"]).strip().lower()
            paciente = str(fila["PACIENTE"]).strip()
            pabellon = str(fila["PABELLON"]).strip()
            cama = str(fila["CAMA"]).strip()
            dieta_original = str(fila["DIETA"]).strip()
            dieta_normalizada = normalizar(dieta_original)

            if "Dieta_Normalizada" in catalogo.columns and dieta_normalizada:
                coincidencia = catalogo[catalogo["Dieta_Normalizada"] == dieta_normalizada]
            else:
                coincidencia = pd.DataFrame()

            if not coincidencia.empty:
                dieta_final = coincidencia.iloc[0]["Dieta"]
            else:
                dieta_final = dieta_original

            observaciones = str(fila["OBSERVACIONES"]).strip() if not pd.isna(fila["OBSERVACIONES"]) else ""
            id_paciente = str(fila["ID"]).strip()

            nuevo = {
                "ID Pedido": str(uuid.uuid4())[:8],
                "Fecha Solicitud": hoy,
                "Fecha Entrega": hoy,
                "Hora Entrega Real": "",
                "Hora Recogida Menaje": "",
                "Cama": cama,
                "Servicio": servicio_detectado,
                "Dietas": dieta_final,
                "Cantidad": 1,
                "Precio Unitario Total": "",
                "Valor Total": "",
                "Estado Entrega": "Pendiente",
                "Estado Recogida": "Pendiente",
                "Tiempo Servicio (min)": "",
                "Condición Menaje": "Desechable" if aislado == "sí" else "Normal",
                "Observaciones": observaciones,
                "Observaciones Menaje": "",
                "Firmado por Enfermería": "No",
                "Paciente": paciente,
                "ID Paciente": id_paciente,
                "Pabellón": pabellon,
                "CDS": cds
            }

            nuevos_pedidos.append(nuevo)

        except Exception as e:
            print(f"⚠️ Error en fila {index + 1}: {e}")

    df_nuevos = pd.DataFrame(nuevos_pedidos)
    df_final = pd.concat([df_pedidos, df_nuevos], ignore_index=True)
    df_final.to_csv(DATA_FILE, index=False, sep=";", encoding="latin1")

    fin = time()
    print(f"⏱️ Tiempo de carga del censo: {fin - inicio:.2f} segundos")
    print(f"✔️ Total registros cargados: {len(nuevos_pedidos)} nuevos / {len(df_final)} en total")

    return redirect("/ver_pedidos")
import unicodedata

def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.strip().lower()
@pedidos_bp.route("/editar/<id>")
def editar(id):
    DATA_FILE = os.path.join("data", "pedidos.csv")
    print("ID recibido:", id)

    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    filtro = df[df["ID Pedido"] == id]
    if filtro.empty:
        return f"Pedido con ID {id} no encontrado", 404

    pedido = filtro.iloc[0].to_dict()
    return render_template("editar_pedido.html", pedido=pedido)

@pedidos_bp.route("/actualizar/<id>", methods=["POST"])
def actualizar(id):
    DATA_FILE = os.path.join("data", "pedidos.csv")
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    print("Columnas del DataFrame después de lectura:", df.columns.tolist())

    index = df[df["ID Pedido"] == id].index[0]
    df.at[index, "Hora Entrega Real"] = request.form["hora_entrega"]
    df.at[index, "Hora Recogida Menaje"] = request.form["hora_recogida"]
    df.at[index, "Estado Recogida"] = request.form["estado_recogida"]
    df.at[index, "Condición Menaje"] = request.form["condicion_menaje"]
    df.at[index, "Observaciones Menaje"] = request.form["observaciones_menaje"]
    df.at[index, "Firmado por Enfermería"] = "Sí" if request.form.get("firmado") else "No"
    df.at[index, "Paciente"] = request.form["paciente"]
    df.at[index, "Pabellón"] = request.form["pabellon"]
    df.at[index, "Servicio"] = request.form["servicio"]
    df.at[index, "Dietas"] = request.form["dietas"]

    df.to_csv(DATA_FILE, index=False, sep=";", encoding="latin1")
    return redirect("/ver_pedidos")

@pedidos_bp.route("/rotulos", methods=["GET", "POST"])
def rotulos():
    DATA_FILE = os.path.join("data", "pedidos.csv")
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"]).dt.date

    if request.method == "POST":
        fecha_ini = request.form.get("fecha_ini")
        fecha_fin = request.form.get("fecha_fin")
        servicio_filtro = request.form.get("servicio")
        dieta_filtro = request.form.get("dieta")
    else:
        fecha_ini = fecha_fin = ""
        servicio_filtro = "Todos"
        dieta_filtro = "Todas"

    detalle = df.copy()
    if fecha_ini:
        detalle = detalle[detalle["Fecha Solicitud"] >= pd.to_datetime(fecha_ini).date()]
    if fecha_fin:
        detalle = detalle[detalle["Fecha Solicitud"] <= pd.to_datetime(fecha_fin).date()]
    if servicio_filtro != "Todos":
        detalle = detalle[detalle["Servicio"] == servicio_filtro]
    if dieta_filtro != "Todas":
        detalle = detalle[detalle["Dietas"].str.contains(dieta_filtro)]

    servicios = sorted(df["Servicio"].dropna().unique())
    dietas = sorted(set([d.strip() for lista in df["Dietas"].dropna() for d in str(lista).split(",")]))
    print("Columnas disponibles en rótulos:", df.columns.tolist())

    return render_template("rotulos.html", pedidos=detalle.to_dict(orient="records"),
                           servicios=servicios, dietas=dietas,
                           fecha_ini=fecha_ini, fecha_fin=fecha_fin,
                           servicio_actual=servicio_filtro, dieta_actual=dieta_filtro)
