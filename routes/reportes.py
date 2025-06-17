from flask import Blueprint, render_template, request,  redirect, url_for, session
import pandas as pd
import os
from datetime import datetime
from services.catalogo import cargar_catalogo
from services.utils import normalizar

reportes_bp = Blueprint("reportes", __name__)

@reportes_bp.route("/reporte_diario", methods=["GET", "POST"])
def reporte_diario():
    DATA_FILE = os.path.join("data", "pedidos.csv")
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"])

    catalogo = cargar_catalogo()
    catalogo["Dieta_Normalizada"] = catalogo["Dieta"].apply(normalizar)

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

    df["Dietas"] = df["Dietas"].apply(corregir_dieta)

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

    resumen_total = detalle.groupby(["Fecha", "Servicio", "Dieta"]).agg({
        "Cantidad": "sum",
        "Valor Total": "sum"
    }).reset_index()

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
@reportes_bp.route("/orden_produccion", methods=["GET", "POST"])
def orden_produccion():
    DATA_FILE = os.path.join("data", "pedidos.csv")
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"]).dt.date

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

    produccion = detalle.groupby(["Fecha", "Dieta", "Servicio"]).agg({
        "Cantidad": "sum"
    }).reset_index()

    produccion.to_excel("static/orden_produccion.xlsx", index=False)

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

@reportes_bp.route("/totalizar", methods=["GET", "POST"])
def totalizar():
    DATA_FILE = os.path.join("data", "pedidos.csv")
    df = pd.read_csv(DATA_FILE, sep=";", encoding="latin1")
    cds_actual = session.get("cds", "")
    if cds_actual:
        df = df[df["CDS"] == cds_actual]

    catalogo = cargar_catalogo()
    catalogo["Dieta_Normalizada"] = catalogo["Dieta"].apply(lambda x: x.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").strip())

    df["Fecha Solicitud"] = pd.to_datetime(df["Fecha Solicitud"]).dt.date

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

    if request.method == "POST":
        fecha_ini = request.form.get("fecha_ini")
        fecha_fin = request.form.get("fecha_fin")
        servicio_filtro = request.form.get("servicio")
        dieta_filtro = request.form.get("dieta")
    else:
        fecha_ini = fecha_fin = ""
        servicio_filtro = "Todos"
        dieta_filtro = "Todas"

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

    if fecha_ini:
        detalle = detalle[detalle["Fecha"] >= pd.to_datetime(fecha_ini).date()]
    if fecha_fin:
        detalle = detalle[detalle["Fecha"] <= pd.to_datetime(fecha_fin).date()]
    if servicio_filtro != "Todos":
        detalle = detalle[detalle["Servicio"] == servicio_filtro]
    if dieta_filtro != "Todas":
        detalle = detalle[detalle["Dieta"].str.contains(dieta_filtro)]

    if detalle.empty:
        resumen = pd.DataFrame(columns=["Fecha", "Servicio", "Dieta", "Cantidad", "Valor Total"])
        total_diario = pd.DataFrame(columns=["Fecha", "Total Venta Día"])
    else:
        resumen = detalle.groupby(["Fecha", "Servicio", "Dieta"]).agg({
            "Cantidad": "sum",
            "Valor Total": "sum"
    }).reset_index()

    total_diario = resumen.groupby("Fecha")["Valor Total"].sum().reset_index()
    total_diario.columns = ["Fecha", "Total Venta Día"]


    resumen.to_excel("static/totalizacion.xlsx", index=False)

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
