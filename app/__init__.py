from flask import Flask

def create_app():
    app = Flask(__name__)

    # Import routes & register blueprint
    from app.routes import routes
    app.register_blueprint(routes)

    return app
