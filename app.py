from flask import Flask, render_template, request, redirect, session, url_for

import pandas as pd
from datetime import datetime
import os
import uuid
import unicodedata

import os
from werkzeug.utils import secure_filename
from datetime import datetime

def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().upper()
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura_123'  # cámbiala en producción

def cargar_sedes():
    df = pd.read_csv("cds.csv", encoding="latin1")
    return list(zip(df["codigo"], df["nombre"]))

DATA_FILE = "data/pedidos.csv"
CATALOGO_FILE = "data/catalogo.csv"
USUARIOS = {
    "admin": "Onedata25"
}

@app.route("/login", methods=["GET"])
def mostrar_login():
    sedes = cargar_sedes()
    return render_template("login.html", sedes=sedes)



@app.route("/login", methods=["POST"])
def login():
    if "usuario" not in request.form or "password" not in request.form:
        return redirect(url_for("login"))

    usuario = request.form["usuario"]
    password = request.form["password"]
    cds = request.form["cds"]

    if usuario == "admin" and password == "Onedata25":
        session["usuario"] = usuario
        session["cds"] = cds
        return redirect("/")
    else:
        return "Usuario o contraseña incorrectos", 401


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.before_request
def proteger_rutas():
    rutas_libres = ["/login", "/static", "/favicon.ico"]
    if request.path in rutas_libres or request.path.startswith("/static"):
        return  # permitir acceso libre

    if not session.get("usuario"):
        if request.endpoint != "login" or request.method != "GET":
            return redirect(url_for("login"))

@app.before_request
def log_ruta():
    print(f"➡️ Solicitud recibida: {request.method} {request.path}")


@app.route("/")
def index():
    print("✅ Entrando a la función INDEX correctamente")
    catalogo = pd.read_csv(CATALOGO_FILE, encoding="latin1", sep=";")
    print("Columnas del catálogo:", catalogo.columns.tolist())

    servicios = catalogo["Servicio"].dropna().unique()
    dietas = catalogo["Dieta"].dropna().unique()
    
    return render_template("index.html", servicios=servicios, dietas=dietas)

@app.route("/cargar_manual", methods=["POST"])
def cargar_manual():
    data = pd.read_csv(DATA_FILE,sep=";", encoding="latin1")
    catalogo = pd.read_csv(CATALOGO_FILE, encoding="latin1" , sep=";")

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

def calcular_tiempo(hora1, hora2):
    try:
        fmt = "%H:%M"
        h1 = datetime.strptime(hora1, fmt)
        h2 = datetime.strptime(hora2, fmt)
        return int((h2 - h1).total_seconds() // 60)
    except:
        return ""


@app.route("/ver_pedidos")
def ver_pedidos():
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    pedidos = df.to_dict(orient="records")
    return render_template("ver_pedidos.html", pedidos=pedidos)


@app.route("/cargar_censo", methods=["GET", "POST"])
def cargar_censo():
    if request.method == "GET":
        return render_template("cargar_censo.html")

    archivo = request.files["archivo"]
    if not archivo:
        return "No se ha seleccionado ningún archivo", 400

    filename = secure_filename(archivo.filename)
    extension = filename.split(".")[-1].lower()
    nombre_archivo = filename.lower()
    if "almuerzo" in nombre_archivo: servicio_detectado = "Almuerzo"
    elif "cena" in nombre_archivo: servicio_detectado = "Cena"

    else: servicio_detectado = "Desayuno"  # Por defecto si no detecta otro


    if extension in ["xls", "xlsx"]:
        df = pd.read_excel(archivo, engine="openpyxl")
    else:
        return "Tipo de archivo no soportado. Usa un archivo Excel (.xlsx o .xls)", 400

    print("Contenido leído del archivo:")
    print(df.head(10))

    df.columns = [col.upper().strip()
    
                  .replace("Á", "A").replace("É", "E")
                  .replace("Í", "I").replace("Ó", "O")
                  .replace("Ú", "U")
                  for col in df.columns]
    print("Columnas del censo:", df.columns.tolist())

    columnas_requeridas = {"ID", "PACIENTE", "PABELLON", "CAMA", "AISLADO", "DIETA", "OBSERVACIONES"}
    if not columnas_requeridas.issubset(set(df.columns)):
        return f"El archivo no contiene todas las columnas requeridas. Columnas encontradas: {df.columns.tolist()}", 400

    try:
        df_pedidos = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
        df_pedidos = df_pedidos.loc[:, ~df_pedidos.columns.str.contains("Unnamed")]
        df_pedidos = df_pedidos.loc[:, ~df_pedidos.columns.str.contains(",")]
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

    from time import time  # Solo si no está ya importado

    inicio = time()
    for index, fila in df.iterrows():
        try:
            aislado = str(fila["AISLADO"]).strip().lower()
            paciente = str(fila["PACIENTE"]).strip()
            pabellon = str(fila["PABELLON"]).strip()
            cama = str(fila["CAMA"]).strip()
            dieta_original = str(fila["DIETA"]).strip()
            dieta_normalizada = normalizar(dieta_original)

# Normalizar catálogo
            catalogo = pd.read_csv(CATALOGO_FILE, sep=";", encoding="latin1")
            catalogo["Dieta_Normalizada"] = catalogo["Dieta"].apply(normalizar)

# Buscar la mejor coincidencia
            coincidencia = catalogo[catalogo["Dieta_Normalizada"] == dieta_normalizada]

            if not coincidencia.empty:
               dieta_final = coincidencia.iloc[0]["Dieta"]  # Usamos el nombre bonito del catálogo
            else:
               dieta_final = dieta_original  # Si no hay coincidencia, dejamos como viene

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
                "ID Paciente": id_paciente,  # 👈 Aquí agregas la línea
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



@app.route("/editar/<id>")
def editar(id):
    print("ID recibido:", id)

    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    filtro = df[df["ID Pedido"] == id]
    if filtro.empty:
       return f"Pedido con ID {id} no encontrado", 404
    pedido = filtro.iloc[0].to_dict()

    return render_template("editar_pedido.html", pedido=pedido)

@app.route("/actualizar/<id>", methods=["POST"])
def actualizar(id):
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

def corregir_dieta(dietas_raw):
    dietas_raw = str(dietas_raw)
    dietas = [d.strip() for d in dietas_raw.split(",") if d.strip()]
    dietas_corregidas = []
    for dieta in dietas:
        dieta_norm = normalizar(dieta)
        match = catalogo[catalogo["Dieta_Normalizada"] == dieta_norm]
        if not match.empty:
            dieta_corregida = match.iloc[0]["Dieta"]
        else:
            dieta_corregida = dieta  # Dejar como está si no encuentra
        dietas_corregidas.append(dieta_corregida)
    return ", ".join(dietas_corregidas)


@app.route("/reporte_diario", methods=["GET", "POST"])
def reporte_diario():
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"])

    # Cargar y normalizar catálogo
    catalogo = pd.read_csv(CATALOGO_FILE, sep=";", encoding="latin1")
    catalogo["Dieta_Normalizada"] = catalogo["Dieta"].apply(normalizar)

    # Definir función interna para corregir dietas
    def corregir_dieta(dietas_raw):
        dietas_raw = str(dietas_raw)
        dietas = [d.strip() for d in dietas_raw.split(",") if d.strip()]
        dietas_corregidas = []
        for dieta in dietas:
            dieta_norm = normalizar(dieta)
            match = catalogo[catalogo["Dieta_Normalizada"] == dieta_norm]
            if not match.empty:
                dieta_corregida = match.iloc[0]["Dieta"]
            else:
                dieta_corregida = dieta
            dietas_corregidas.append(dieta_corregida)
        return ", ".join(dietas_corregidas)

    # Aplicar corrección
    df["Dietas"] = df["Dietas"].apply(corregir_dieta)

    # Expandir dietas combinadas
    filas = []
    for _, row in df.iterrows():
        dietas_raw = str(row["Dietas"]) if not pd.isna(row["Dietas"]) else ""
        dietas = [d.strip() for d in dietas_raw.split(",") if d.strip()]
        for dieta in dietas:
            filas.append({
                "Fecha": row["Fecha Solicitud"].date(),
                "Servicio": row["Servicio"],
                "Dieta": dieta,
                "Cantidad": row["Cantidad"],
                "Valor Total": row["Valor Total"]
            })
    detalle = pd.DataFrame(filas)

    # Consolidado sin filtros
    resumen_total = detalle.groupby(["Fecha", "Servicio", "Dieta"]).agg({
        "Cantidad": "sum",
        "Valor Total": "sum"
    }).reset_index()

    # Filtros
    if request.method == "POST":
        fecha_ini = request.form.get("fecha_ini")
        fecha_fin = request.form.get("fecha_fin")
        servicio_filtro = request.form.get("servicio")
        dieta_filtro = request.form.get("dieta")

        if fecha_ini:
            detalle = detalle[detalle["Fecha"] >= pd.to_datetime(fecha_ini).date()]
        if fecha_fin:
            detalle = detalle[detalle["Fecha"] <= pd.to_datetime(fecha_fin).date()]
        if servicio_filtro and servicio_filtro != "Todos":
            detalle = detalle[detalle["Servicio"] == servicio_filtro]
        if dieta_filtro and dieta_filtro != "Todas":
            detalle = detalle[detalle["Dieta"] == dieta_filtro]
    else:
        fecha_ini = ""
        fecha_fin = ""
        servicio_filtro = "Todos"
        dieta_filtro = "Todas"

    resumen = detalle.groupby(["Fecha", "Servicio", "Dieta"]).agg({
        "Cantidad": "sum",
        "Valor Total": "sum"
    }).reset_index()

    resumen.to_excel("static/reporte_diario.xlsx", index=False)

    servicios = sorted(df["Servicio"].dropna().unique())
    dietas = sorted(set([d.strip() for lista in df["Dietas"].dropna() for d in str(lista).split(",")]))

    return render_template("reporte_diario.html",
                           resumen=resumen.to_dict(orient="records"),
                           resumen_total=resumen_total.to_dict(orient="records"),
                           servicios=servicios, dietas=dietas,
                           fecha_ini=fecha_ini, fecha_fin=fecha_fin,
                           servicio_actual=servicio_filtro,
                           dieta_actual=dieta_filtro)


# Orden de Producción - Agrupada por Fecha, Dieta y Servicio
@app.route("/orden_produccion", methods=["GET", "POST"])
def orden_produccion():
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"]).dt.date

    # Expandir combinaciones de dietas
    filas = []
    for _, row in df.iterrows():
        dietas_raw = str(row["Dietas"]) if not pd.isna(row["Dietas"]) else ""
        dietas = [d.strip() for d in dietas_raw.split(",") if d.strip()]
        for dieta in dietas:
            filas.append({
                "Fecha": row["Fecha Solicitud"],
                "Dieta": dieta,
                "Servicio": row["Servicio"],
                "Cantidad": row["Cantidad"]
            })

    detalle = pd.DataFrame(filas)

    # Aplicar filtros si se usan
    if request.method == "POST":
        fecha_ini = request.form.get("fecha_ini")
        fecha_fin = request.form.get("fecha_fin")
        servicio_filtro = request.form.get("servicio")
        dieta_filtro = request.form.get("dieta")
    else:
        fecha_ini = ""
        fecha_fin = ""
        servicio_filtro = "Todos"
        dieta_filtro = "Todas"

    if fecha_ini:
        detalle = detalle[detalle["Fecha"] >= pd.to_datetime(fecha_ini).date()]
    if fecha_fin:
        detalle = detalle[detalle["Fecha"] <= pd.to_datetime(fecha_fin).date()]
    if servicio_filtro != "Todos":
        detalle = detalle[detalle["Servicio"] == servicio_filtro]
    if dieta_filtro != "Todas":
        detalle = detalle[detalle["Dieta"].str.contains(dieta_filtro)]

    # Agrupar producción final
    produccion = detalle.groupby(["Fecha", "Dieta", "Servicio"]).agg({
        "Cantidad": "sum"
    }).reset_index()

    # Exportar a Excel
    produccion.to_excel("static/orden_produccion.xlsx", index=False)

    # Listas para filtros
    servicios = sorted(df["Servicio"].dropna().unique())
    dietas = sorted(set([d.strip() for lista in df["Dietas"].dropna() for d in str(lista).split(",")]))

    return render_template("orden_produccion.html",
                           produccion=produccion.to_dict(orient="records"),
                           servicios=servicios,
                           dietas=dietas,
                           fecha_ini=fecha_ini,
                           fecha_fin=fecha_fin,
                           servicio_actual=servicio_filtro,
                           dieta_actual=dieta_filtro)


@app.route("/rotulos", methods=["GET", "POST"])
def rotulos():
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"]).dt.date

    # Filtros del formulario
    if request.method == "POST":
        fecha_ini = request.form.get("fecha_ini")
        fecha_fin = request.form.get("fecha_fin")
        servicio_filtro = request.form.get("servicio")
        dieta_filtro = request.form.get("dieta")
    else:
        fecha_ini = fecha_fin = ""
        servicio_filtro = "Todos"
        dieta_filtro = "Todas"

    # Aplicar filtros
    detalle = df.copy()
    if fecha_ini:
        detalle = detalle[detalle["Fecha Solicitud"] >= pd.to_datetime(fecha_ini).date()]
    if fecha_fin:
        detalle = detalle[detalle["Fecha Solicitud"] <= pd.to_datetime(fecha_fin).date()]
    if servicio_filtro != "Todos":
        detalle = detalle[detalle["Servicio"] == servicio_filtro]
    if dieta_filtro != "Todas":
        detalle = detalle[detalle["Dietas"].str.contains(dieta_filtro)]

    # Obtener listas para los select del formulario
    servicios = sorted(df["Servicio"].dropna().unique())
    dietas = sorted(set([d.strip() for lista in df["Dietas"].dropna() for d in str(lista).split(",")]))
    print("Columnas disponibles en rótulos:", df.columns.tolist())

    return render_template("rotulos.html", pedidos=detalle.to_dict(orient="records"),
                           servicios=servicios, dietas=dietas,
                           fecha_ini=fecha_ini, fecha_fin=fecha_fin,
                           servicio_actual=servicio_filtro, dieta_actual=dieta_filtro)

# Vista de Totalización filtrable con lógica de precio más alto por combinación

@app.route("/totalizar", methods=["GET", "POST"])
def totalizar():
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    catalogo = pd.read_csv(CATALOGO_FILE, sep=";", encoding="latin1")

    # Normalizar catálogo
    catalogo["Dieta_Normalizada"] = catalogo["Dieta"].apply(lambda x: x.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").strip())

    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"]).dt.date

    # Normalizar dietas del pedido
    def corregir_dieta(dietas_raw):
        dietas_raw = str(dietas_raw)
        dietas = [d.strip() for d in dietas_raw.split(",") if d.strip()]
        dietas_corregidas = []
        for dieta in dietas:
            dieta_norm = dieta.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").strip()
            match = catalogo[catalogo["Dieta_Normalizada"] == dieta_norm]
            if not match.empty:
                dieta_corregida = match.iloc[0]["Dieta"]
            else:
                dieta_corregida = dieta
            dietas_corregidas.append(dieta_corregida)
        return ", ".join(dietas_corregidas)

    df["Dietas"] = df["Dietas"].apply(corregir_dieta)

    # Leer filtros
    if request.method == "POST":
        fecha_ini = request.form.get("fecha_ini")
        fecha_fin = request.form.get("fecha_fin")
        servicio_filtro = request.form.get("servicio")
        dieta_filtro = request.form.get("dieta")
    else:
        fecha_ini = fecha_fin = ""
        servicio_filtro = "Todos"
        dieta_filtro = "Todas"

    # Expandir y calcular el precio mayor
    filas = []
    for _, row in df.iterrows():
        dietas_raw = str(row["Dietas"]) if not pd.isna(row["Dietas"]) else ""
        dietas = [d.strip() for d in dietas_raw.split(",") if d.strip()]

        precios = []
        for dieta in dietas:
            match = catalogo[(catalogo["Servicio"] == row["Servicio"]) & (catalogo["Dieta"] == dieta)]
            if not match.empty:
                precios.append(match["Precio"].values[0])

        valor_total = max(precios) * row["Cantidad"] if precios else 0

        filas.append({
            "Fecha": row["Fecha Solicitud"],
            "Servicio": row["Servicio"],
            "Dieta": ", ".join(dietas),
            "Cantidad": row["Cantidad"],
            "Valor Total": valor_total
        })

    detalle = pd.DataFrame(filas)

    # Aplicar filtros
    if fecha_ini:
        detalle = detalle[detalle["Fecha"] >= pd.to_datetime(fecha_ini).date()]
    if fecha_fin:
        detalle = detalle[detalle["Fecha"] <= pd.to_datetime(fecha_fin).date()]
    if servicio_filtro != "Todos":
        detalle = detalle[detalle["Servicio"] == servicio_filtro]
    if dieta_filtro != "Todas":
        detalle = detalle[detalle["Dieta"].str.contains(dieta_filtro)]

    resumen = detalle.groupby(["Fecha", "Servicio", "Dieta"]).agg({
        "Cantidad": "sum",
        "Valor Total": "sum"
    }).reset_index()

    resumen.to_excel("static/totalizacion.xlsx", index=False)

    # Crear tabla de total de ventas por día
    total_diario = resumen.groupby("Fecha")["Valor Total"].sum().reset_index()
    total_diario.columns = ["Fecha", "Total Venta Día"]
    servicios = sorted(df["Servicio"].dropna().unique())
    dietas = sorted(set([d.strip() for lista in df["Dietas"].dropna() for d in str(lista).split(",")]))

    return render_template("totalizar.html",
                           total=resumen.to_dict(orient="records"),
                           total_diario=total_diario.to_dict(orient="records"),
                           servicios=servicios, dietas=dietas,
                           fecha_ini=fecha_ini, fecha_fin=fecha_fin,
                           servicio_actual=servicio_filtro,
                           dieta_actual=dieta_filtro)
    
    

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')


    

  