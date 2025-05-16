from flask import Blueprint, render_template, request
import pandas as pd
from datetime import datetime

rotulos_bp = Blueprint("rotulos", __name__)

@rotulos_bp.route("/rotulos", methods=["GET", "POST"])
def rotulos():
    df = pd.read_csv("data/pedidos.csv", sep=";", encoding="latin1")
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

    # Filtros
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

    return render_template("rotulos.html",
                           pedidos=detalle.to_dict(orient="records"),
                           servicios=servicios, dietas=dietas,
                           fecha_ini=fecha_ini, fecha_fin=fecha_fin,
                           servicio_actual=servicio_filtro,
                           dieta_actual=dieta_filtro)
