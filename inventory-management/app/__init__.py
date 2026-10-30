from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.routes.products import products_bp
    from app.routes.suppliers import suppliers_bp
    from app.routes.transactions import transactions_bp
    from app.routes.purchase_orders import purchase_orders_bp
    from app.routes.views import views_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(products_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(purchase_orders_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(reports_bp)

    return app
