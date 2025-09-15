"""
WSGI entry point for the Flask application.
This file allows the Flask app to be served by WSGI servers like Gunicorn, uWSGI, or Waitress.
"""

from app import app

# Initialize database tables when the WSGI server starts
with app.app_context():
    try:
        from models import db
        db.create_all()
        print("Database tables initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize database tables: {e}")

if __name__ == "__main__":
    app.run()
