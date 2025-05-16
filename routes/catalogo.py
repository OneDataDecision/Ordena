from flask import Blueprint, render_template

catalogo_bp = Blueprint("catalogo", __name__)

@catalogo_bp.route("/catalogo")
def catalogo():
    return render_template("catalogo.html")

import pandas as pd
import os

def cargar_catalogo():
    catalogo_path = os.path.join("data", "catalogo.csv")
    return pd.read_csv(catalogo_path, sep=";", encoding="latin1")
