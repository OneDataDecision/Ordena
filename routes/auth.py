from flask import Blueprint, render_template, request, redirect, session, url_for
import os
import pandas as pd

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    ruta_cds = os.path.join("data", "cds.csv")
    cds_disponibles = pd.read_csv(ruta_cds, encoding="latin1").to_dict(orient="records")

    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        clave = request.form.get("clave", "")
        cds_codigo = request.form.get("cds", "")

        if usuario == "admin" and clave == "Onedata25":
            cds_nombre = next((item["nombre"] for item in cds_disponibles if str(item["codigo"]) == cds_codigo), "CDS desconocido")

            session["usuario"] = usuario
            session["cds"] = cds_codigo
            session["cds_nombre"] = cds_nombre  # ✅ Útil para mostrarlo luego

            return redirect(url_for("pedidos.inicio"))


        else:
            return render_template("login.html", cds=cds_disponibles, error="Credenciales incorrectas")

    return render_template("login.html", cds=cds_disponibles)

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

from flask import request, redirect, session, url_for

@auth_bp.before_app_request
def verificar_sesion():
    rutas_publicas = ["/", "/login", "/favicon.ico"]
    if request.path in rutas_publicas or request.path.startswith("/static"):
        return  # permitir acceso

    if "cds" not in session:  # 👈 o "usuario", según lo que uses
        return redirect(url_for("auth.login"))
