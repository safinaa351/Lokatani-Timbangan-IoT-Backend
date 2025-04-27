from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def create_app():
    app = Flask(__name__)
    
    # Initialize limiter
    limiter.init_app(app)

    # Import routes & register blueprints
    from app.routes import routes
    from app.routes_iot import iot_routes
    
    app.register_blueprint(routes)
    app.register_blueprint(iot_routes)

    return app