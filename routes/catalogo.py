from flask import Blueprint, render_template, request
import pandas as pd
import os

catalogo_bp = Blueprint("catalogo", __name__)

@catalogo_bp.route("/ver_catalogo", methods=["GET"])
def ver_catalogo_html():
    ruta = os.path.join("data", "catalogo.csv")
    df = pd.read_csv(ruta, sep=";", encoding="latin1")

    # Filtros desde query params
    servicio = request.args.get("servicio", "")
    dieta = request.args.get("dieta", "")

    # Aplicar filtros si existen
    if servicio:
        df = df[df["Servicio"] == servicio]
    if dieta:
        df = df[df["Dieta"] == dieta]

    # Obtener listas únicas para los filtros
    servicios_unicos = df["Servicio"].dropna().unique().tolist()
    dietas_unicas = df["Dieta"].dropna().unique().tolist()

    return render_template(
        "catalogo.html",
        catalogo=df.to_dict(orient="records"),
        servicios=servicios_unicos,
        dietas=dietas_unicas,
        servicio_actual=servicio,
        dieta_actual=dieta
    )
