from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
import os

# Import models and routes
from models import db
from routes import register_routes
from config import get_config, get_environment_info

# Get configuration
config = get_config()

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Apply configuration
app.config.from_object(config)

# Static files configuration for image serving
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app, origins=config.CORS_ORIGINS)

# Register all routes
register_routes(app)

if __name__ == '__main__':
    # Print environment info
    env_info = get_environment_info()
    print("=" * 50)
    print("Student Event Networking Backend")
    print("=" * 50)
    print(f"Environment Mode: {env_info['mode']}")
    print(f"Environment: {env_info['environment']}")
    print(f"Debug Mode: {env_info['debug']}")
    print(f"Host: {env_info['host']}")
    print(f"Port: {env_info['port']}")
    print(f"Database: {env_info['database_uri']}")
    print(f"Push Notifications: {env_info['push_notifications_enabled']}")
    print("=" * 50)
    
    # Initialize database only when running directly
    with app.app_context():
        db.create_all()
    
    # Run the app
    app.run(
        host=config.HOST, 
        port=config.PORT, 
        debug=config.DEBUG
    )
