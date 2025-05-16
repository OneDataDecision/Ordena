from .pedidos import pedidos_bp

def register_routes(app):
    app.register_blueprint(pedidos_bp)
from .reportes import reportes_bp
def register_routes(app):
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(reportes_bp)
from .inicio import inicio_bp  # 👈 Agrega esta línea
