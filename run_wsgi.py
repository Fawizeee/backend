"""
Script to run the Flask application with different WSGI servers.
"""

import os
import sys
import subprocess

def run_gunicorn():
    """Run with Gunicorn (recommended for production)"""
    cmd = [
        "gunicorn",
        "--config", "gunicorn.conf.py",
        "wsgi:app"
    ]
    subprocess.run(cmd)

def run_waitress():
    """Run with Waitress (good for Windows, pure Python)"""
    try:
        from waitress import serve
        from wsgi import app
        
        print("Starting Waitress WSGI server...")
        print("Server will be available at: http://0.0.0.0:5000")
        print("Press Ctrl+C to stop the server")
        serve(app, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"Error starting Waitress server: {e}")
        import traceback
        traceback.print_exc()

def run_development():
    """Run with Flask development server"""
    from wsgi import app
    app.run(host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        server = sys.argv[1].lower()
        if server == "gunicorn":
            run_gunicorn()
        elif server == "waitress":
            run_waitress()
        elif server == "dev":
            run_development()
        else:
            print("Usage: python run_wsgi.py [gunicorn|waitress|dev]")
    else:
        print("Available WSGI servers:")
        print("  python run_wsgi.py gunicorn  - Run with Gunicorn (production)")
        print("  python run_wsgi.py waitress - Run with Waitress (Windows-friendly)")
        print("  python run_wsgi.py dev      - Run with Flask dev server")
