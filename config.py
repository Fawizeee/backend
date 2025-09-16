"""
Configuration file for the Student Event Networking Backend
This file contains environment-specific configuration values
"""

import os
from datetime import timedelta

# Environment Configuration
# Change this value to switch between environments: 'lh' for localhost, 'prod' for production
ENVIRONMENT_MODE = ''  # Options: 'lh' (localhost) or 'prod' (production)

# Environment-specific configurations
# Change this value to switch between environments: 'lh' for localhost, 'prod' for production
ENVIRONMENTS = {
    'lh': {
        'DEBUG': True,
        'HOST': '0.0.0.0',
        'PORT': 5000,
        'DATABASE_URI': 'sqlite:///student_events.db',
        'JWT_SECRET_KEY': 'your-secret-key-change-this-localhost',
        'CORS_ORIGINS': ['*'],  # Allow all origins in development
        'UPLOAD_FOLDER': 'static/uploads',
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
        'PUSH_NOTIFICATIONS_ENABLED': True,
        'LOG_LEVEL': 'DEBUG',
    },
    'prod': {
        'DEBUG': False,
        'HOST': '0.0.0.0',
        'PORT': int(os.environ.get('PORT', 5000)),
        'DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///student_events.db'),
        'JWT_SECRET_KEY': os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-this-production'),
        'CORS_ORIGINS': ['https://your-frontend-domain.com'],  # Add your production frontend domain
        'UPLOAD_FOLDER': 'static/uploads',
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
        'PUSH_NOTIFICATIONS_ENABLED': True,
        'LOG_LEVEL': 'INFO',
    }
}

# Get current environment configuration
current_env = ENVIRONMENTS.get(ENVIRONMENT_MODE, ENVIRONMENTS['prod'])

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = current_env['JWT_SECRET_KEY']
    DEBUG = current_env['DEBUG']
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = current_env['DATABASE_URI']
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = current_env['JWT_SECRET_KEY']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    
    # CORS Configuration
    CORS_ORIGINS = current_env['CORS_ORIGINS']
    
    # File Upload Configuration
    UPLOAD_FOLDER = current_env['UPLOAD_FOLDER']
    MAX_CONTENT_LENGTH = current_env['MAX_CONTENT_LENGTH']
    
    # Push Notifications
    PUSH_NOTIFICATIONS_ENABLED = current_env['PUSH_NOTIFICATIONS_ENABLED']
    
    # Logging
    LOG_LEVEL = current_env['LOG_LEVEL']
    
    # Server Configuration
    HOST = current_env['HOST']
    PORT = current_env['PORT']
    
    # Environment Info
    ENVIRONMENT_MODE = ENVIRONMENT_MODE
    ENVIRONMENT = 'localhost' if ENVIRONMENT_MODE == 'lh' else 'production'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENVIRONMENT = 'localhost'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENVIRONMENT = 'production'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Get current configuration
def get_config():
    """Get the current configuration based on environment mode"""
    if ENVIRONMENT_MODE == 'lh':
        return DevelopmentConfig()
    else:
        return ProductionConfig()

# Environment info
def get_environment_info():
    """Get current environment information"""
    return {
        'mode': ENVIRONMENT_MODE,
        'environment': current_env.get('ENVIRONMENT', 'unknown'),
        'debug': current_env.get('DEBUG', False),
        'host': current_env.get('HOST', 'localhost'),
        'port': current_env.get('PORT', 5000),
        'database_uri': current_env.get('DATABASE_URI', 'sqlite:///student_events.db'),
        'push_notifications_enabled': current_env.get('PUSH_NOTIFICATIONS_ENABLED', True),
    }

# Print environment info on startup
if __name__ == '__main__':
    info = get_environment_info()
    print("=" * 50)
    print("Student Event Networking Backend Configuration")
    print("=" * 50)
    print(f"Environment Mode: {info['mode']}")
    print(f"Environment: {info['environment']}")
    print(f"Debug Mode: {info['debug']}")
    print(f"Host: {info['host']}")
    print(f"Port: {info['port']}")
    print(f"Database: {info['database_uri']}")
    print(f"Push Notifications: {info['push_notifications_enabled']}")
    print("=" * 50)
