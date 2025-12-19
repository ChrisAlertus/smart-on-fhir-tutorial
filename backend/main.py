"""
Flask Backend for SMART on FHIR Tutorial
Handles token validation and FHIR API proxying
"""
from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# CORS configuration - only allow HTTPS origins
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == [""]:
    # Default to localhost for development (can be overridden in .env)
    allowed_origins = [
        "https://localhost:8443",
        "https://127.0.0.1:8443",
        "https://wattless-rotundly-celena.ngrok-free.dev",
        "https://chrisalertus.github.io",  # GitHub Pages
        "http://localhost:8000",  # Allow HTTP for local dev
        "http://127.0.0.1:8000"
    ]

# Filter and clean origins
cleaned_origins = []
for origin in allowed_origins:
    origin = origin.strip()
    if origin and (origin.startswith("https://")
                   or origin.startswith("http://")):
        cleaned_origins.append(origin)

# IMPORTANT: Cannot use "*" with supports_credentials=True
# Must specify exact origins when using credentials
if not cleaned_origins:
    print(
        "WARNING: No CORS origins configured. Using default GitHub Pages origin."
    )
    # Default to GitHub Pages if nothing configured
    cleaned_origins = ["https://chrisalertus.github.io"]

print(f"CORS allowed origins: {cleaned_origins}")
# Note: supports_credentials=False because we use Authorization headers, not cookies
CORS(
    app,
    origins=cleaned_origins,
    supports_credentials=
    False,  # Set to False since we use Authorization headers
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Type"])

# Import blueprints
try:
    # Try absolute import (when running from project root)
    from backend import auth, fhir
except ImportError:
    # Fall back to relative import (when running from backend directory)
    import auth
    import fhir

# Register blueprints
app.register_blueprint(auth.bp, url_prefix="/api/auth")
app.register_blueprint(fhir.bp, url_prefix="/api/fhir")

# Error handlers
from werkzeug.exceptions import HTTPException


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handle HTTP exceptions and return JSON response"""
    return jsonify({"error": e.description}), e.code


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle general exceptions"""
    return jsonify({"error": str(e)}), 500


@app.route("/")
def root():
    """Root endpoint"""
    return jsonify({
        "message": "SMART on FHIR Backend API",
        "version": "1.0.0"
    })


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    # Get SSL configuration from environment
    ssl_certfile = os.getenv("SSL_CERTFILE")
    ssl_keyfile = os.getenv("SSL_KEYFILE")
    port = int(os.getenv("PORT", "8443"))

    # Run with HTTPS if certificates are provided
    # Note: Hosting services like Render/Railway provide SSL automatically via reverse proxy
    if ssl_certfile and ssl_keyfile and os.path.exists(
            ssl_certfile) and os.path.exists(ssl_keyfile):
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(ssl_certfile, ssl_keyfile)

        app.run(host="0.0.0.0", port=port, ssl_context=context, debug=True)
    else:
        # For hosting services (Render, Railway, etc.) that provide SSL via reverse proxy
        # Or for local development without SSL
        if not ssl_certfile or not ssl_keyfile:
            print(
                "INFO: Running without local SSL. Hosting services provide SSL automatically."
            )
        else:
            print("WARNING: SSL certificates not found. Running without SSL.")
        app.run(host="0.0.0.0", port=port, debug=True)
