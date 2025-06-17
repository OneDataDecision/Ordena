from flask import Blueprint, render_template, session, redirect, url_for

inicio_bp = Blueprint("inicio", __name__)

#@inicio_bp.route("/")
#def inicio():
 #   return render_template("inicio.html")

@inicio_bp.route("/inicio")
def vista_inicio():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))
    return render_template("inicio.html")
def inicio_autenticado():
    if "cds" not in session:
        return redirect("/")
    return render_template("inicio.html")
