from flask import Blueprint, render_template
import pandas as pd
import os

catalogo_bp = Blueprint("catalogo", __name__)

@catalogo_bp.route("/catalogo")
def ver_catalogo():
    path = os.path.join("data", "catalogo.csv")
    df = pd.read_csv(path, sep=";", encoding="latin1")  # ajusta si usas coma
    return render_template("catalogo.html", catalogo=df.to_dict(orient="records"))
def cargar_catalogo():
    catalogo_path = os.path.join("data", "catalogo.csv")
    return pd.read_csv(catalogo_path, sep=";", encoding="latin1")
