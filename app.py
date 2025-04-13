from flask import Flask, render_template, request, redirect, session, url_for

import pandas as pd
from datetime import datetime
import os
import uuid

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura_123'  # cámbiala en producción

DATA_FILE = "data/pedidos.csv"
CATALOGO_FILE = "data/catalogo.csv"
USUARIOS = {
    "admin": "Onedata25"
}
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        clave = request.form["clave"]
        if USUARIOS.get(usuario) == clave:
            session["usuario"] = usuario
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Credenciales incorrectas")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.before_request
def proteger_rutas():
    rutas_libres = ["/login", "/static/"]
    if not session.get("usuario") and not request.path.startswith(tuple(rutas_libres)):
        return redirect(url_for("login"))

@app.route("/")
def index():
    catalogo = pd.read_csv(CATALOGO_FILE)
    servicios = catalogo["Servicio"].dropna().unique()
    dietas = catalogo["Dieta"].dropna().unique()
    return render_template("index.html", servicios=servicios, dietas=dietas)

@app.route("/cargar_manual", methods=["POST"])
def cargar_manual():
    data = pd.read_csv(DATA_FILE)
    catalogo = pd.read_csv(CATALOGO_FILE)

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
    data.to_csv(DATA_FILE, index=False)
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
    df = pd.read_csv(DATA_FILE)
    pedidos = df.to_dict(orient="records")
    return render_template("ver_pedidos.html", pedidos=pedidos)

@app.route("/editar/<id>")
def editar(id):
    print("ID recibido:", id)

    df = pd.read_csv(DATA_FILE)
    pedido = df[df["ID Pedido"] == id].iloc[0].to_dict()
    return render_template("editar_pedido.html", pedido=pedido)

@app.route("/actualizar/<id>", methods=["POST"])
def actualizar(id):
    df = pd.read_csv(DATA_FILE)
    index = df[df["ID Pedido"] == id].index[0]

    df.at[index, "Hora Recogida Menaje"] = request.form["hora_recogida"]
    df.at[index, "Estado Recogida"] = request.form["estado_recogida"]
    df.at[index, "Condición Menaje"] = request.form["condicion_menaje"]
    df.at[index, "Observaciones Menaje"] = request.form["observaciones_menaje"]
    df.at[index, "Firmado por Enfermería"] = "Sí" if request.form.get("firmado") else "No"
  
    df.to_csv(DATA_FILE, index=False)
    return redirect("/ver_pedidos")
@app.route("/reporte_diario", methods=["GET", "POST"])
def reporte_diario():
    df = pd.read_csv(DATA_FILE)
    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"])

    # Filtros desde formulario
    fecha_ini = request.form.get("fecha_ini")
    fecha_fin = request.form.get("fecha_fin")
    servicio_filtro = request.form.get("servicio")
    dieta_filtro = request.form.get("dieta")

    # Expandir dietas combinadas
    filas = []
    for _, row in df.iterrows():
        dietas = [d.strip() for d in row["Dietas"].split(",")]
        for dieta in dietas:
            filas.append({
                "Fecha": row["Fecha Solicitud"].date(),
                "Servicio": row["Servicio"],
                "Dieta": dieta,
                "Cantidad": row["Cantidad"],
                "Valor Total": row["Valor Total"]
            })
    detalle = pd.DataFrame(filas)

    # Aplicar filtros si hay
    if fecha_ini:
        detalle = detalle[detalle["Fecha"] >= pd.to_datetime(fecha_ini).date()]
    if fecha_fin:
        detalle = detalle[detalle["Fecha"] <= pd.to_datetime(fecha_fin).date()]
    if servicio_filtro and servicio_filtro != "Todos":
        detalle = detalle[detalle["Servicio"] == servicio_filtro]
    if dieta_filtro and dieta_filtro != "Todas":
        detalle = detalle[detalle["Dieta"] == dieta_filtro]

    # Agrupar
    resumen = detalle.groupby(["Fecha", "Servicio", "Dieta"]).agg({
        "Cantidad": "sum",
        "Valor Total": "sum"
    }).reset_index()

    # Guardar para descarga
    resumen.to_excel("static/reporte_diario.xlsx", index=False)

    # Para los select del formulario
    servicios = sorted(detalle["Servicio"].unique())
    dietas = sorted(detalle["Dieta"].unique())

    return render_template("reporte_diario.html", resumen=resumen.to_dict(orient="records"),
                           servicios=servicios, dietas=dietas,
                           fecha_ini=fecha_ini, fecha_fin=fecha_fin,
                           servicio_actual=servicio_filtro, dieta_actual=dieta_filtro)

    # Expandir dietas combinadas en filas separadas
    filas = []
    for _, row in df.iterrows():
        dietas = [d.strip() for d in row["Dietas"].split(",")]
        for dieta in dietas:
            filas.append({
                "Fecha": row["Fecha Solicitud"].date(),
                "Servicio": row["Servicio"],
                "Dieta": dieta,
                "Cantidad": row["Cantidad"],
                "Valor Total": row["Valor Total"]
            })
    detalle = pd.DataFrame(filas)

    # Agrupar por Fecha, Servicio, Dieta
    resumen = detalle.groupby(["Fecha", "Servicio", "Dieta"]).agg({
        "Cantidad": "sum",
        "Valor Total": "sum"
    }).reset_index()

    # Guardar para exportación
    resumen.to_excel("static/reporte_diario.xlsx", index=False)


    return render_template("reporte_diario.html", resumen=resumen.to_dict(orient="records"))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
    

  