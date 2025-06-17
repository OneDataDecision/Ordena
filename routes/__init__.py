from .pedidos import pedidos_bp
from .auth import auth_bp
from .reportes import reportes_bp
from .inicio import inicio_bp  # 👈 Agrega esta línea
from .rotulos import rotulos_bp
from .catalogo import catalogo_bp
from .usuarios import usuarios_bp
from .menu import menu_bp

def register_routes(app):
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(inicio_bp)
    app.register_blueprint(rotulos_bp)  # 👈 Aquí
    app.register_blueprint(catalogo_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(menu_bp)
