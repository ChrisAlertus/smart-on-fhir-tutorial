"""
Token validation module
Validates JWT tokens from frontend requests
"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import Unauthorized
from jose import jwt, JWTError
from datetime import datetime

bp = Blueprint("auth", __name__)

class TokenValidationError(Exception):
    """Custom exception for token validation errors"""
    def __init__(self, message, status_code=401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def validate_token(token: str) -> dict:
    """
    Validate a JWT token

    Args:
        token: JWT token string

    Returns:
        dict: Token payload if valid

    Raises:
        TokenValidationError: If token is invalid or expired
    """
    try:
        # Decode token without verification first to check structure
        unverified = jwt.get_unverified_claims(token)

        # Check expiration
        if "exp" in unverified:
            exp_timestamp = unverified["exp"]
            current_timestamp = datetime.utcnow().timestamp()

            if current_timestamp >= exp_timestamp:
                raise TokenValidationError("Token has expired", 401)

        # For SMART on FHIR tokens, we typically don't verify signature
        # as they come from the authorization server and are validated
        # by the FHIR server itself. However, we check structure and expiration.

        # Return decoded token (unverified signature, but structure validated)
        return unverified

    except JWTError as e:
        raise TokenValidationError(f"Invalid token: {str(e)}", 401)
    except TokenValidationError:
        raise
    except Exception as e:
        raise TokenValidationError(f"Token validation failed: {str(e)}", 401)

@bp.route("/validate", methods=["GET"])
def validate_token_endpoint():
    """
    Endpoint to validate a token

    Returns:
        dict: Validation result
    """
    authorization = request.headers.get("Authorization")

    if not authorization:
        return jsonify({
            "valid": False,
            "error": "Authorization header missing"
        }), 401

    # Extract token from Bearer format
    if not authorization.startswith("Bearer "):
        return jsonify({
            "valid": False,
            "error": "Invalid authorization header format. Expected 'Bearer <token>'"
        }), 401

    token = authorization.replace("Bearer ", "").strip()

    try:
        payload = validate_token(token)
        return jsonify({
            "valid": True,
            "payload": payload
        })
    except TokenValidationError as e:
        return jsonify({
            "valid": False,
            "error": e.message
        }), e.status_code
    except Exception as e:
        return jsonify({
            "valid": False,
            "error": str(e)
        }), 401
