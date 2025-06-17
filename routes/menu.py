from flask import Blueprint, render_template

# Primero defines el Blueprint
menu_bp = Blueprint('menu', __name__, url_prefix='/menu')

# Luego usas ese blueprint en tu ruta
@menu_bp.route('/')
def mostrar_menu():
    return render_template("menu.html")
