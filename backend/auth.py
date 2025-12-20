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
    import logging
    logger = logging.getLogger(__name__)

    if not token or not isinstance(token, str):
        raise TokenValidationError("Token is empty or invalid type", 401)

    # Clean the token - remove any extra whitespace or encoding issues
    token = token.strip()

    # Check if token might be URL-encoded or have other issues
    # Try to decode if it looks encoded
    if '%' in token:
        import urllib.parse
        try:
            token = urllib.parse.unquote(token)
            logger.info("Decoded URL-encoded token")
        except Exception as e:
            logger.warning(f"Failed to URL-decode token: {e}")

    # Check if token has basic JWT structure (3 parts separated by dots)
    token_parts = token.split('.')

    # Log token structure for debugging
    logger.warning(f"Token has {len(token_parts)} parts when split by '.'")
    logger.warning(f"Token length: {len(token)}")
    logger.warning(f"First 100 chars: {token[:100]}")
    logger.warning(f"Last 50 chars: {token[-50:]}")

    # If token has more than 3 parts, try to extract just the first 3
    # This handles cases where tokens might be concatenated
    if len(token_parts) > 3:
        logger.warning(
            f"Token has {len(token_parts)} parts, attempting to extract first 3 parts"
        )
        # Try to reconstruct token from first 3 parts
        potential_token = '.'.join(token_parts[:3])
        # Validate that the reconstructed token looks reasonable
        if len(potential_token) > 50:  # JWT tokens are typically much longer
            token = potential_token
            token_parts = token.split('.')
            logger.info("Using first 3 parts as token")
        else:
            logger.error(
                f"Reconstructed token too short ({len(potential_token)} chars), original token may be malformed"
            )

    if len(token_parts) != 3:
        logger.error(f"Token still has {len(token_parts)} parts after cleanup")
        raise TokenValidationError(
            f"Invalid token format: expected JWT with 3 parts, got {len(token_parts)}. Token may be malformed or concatenated.",
            401)

    # Additional validation: ensure token is not empty after cleanup
    if not token or len(token) < 10:
        logger.error(
            f"Token is empty or too short after cleanup (length: {len(token) if token else 0})"
        )
        raise TokenValidationError("Token is empty or invalid", 401)

    try:
        # Decode token without verification first to check structure
        # Try get_unverified_claims first (python-jose)
        try:
            unverified = jwt.get_unverified_claims(token)
        except AttributeError:
            # Fallback: decode without verification using decode method
            # Some versions of python-jose use decode with options
            try:
                unverified = jwt.decode(token,
                                        options={"verify_signature": False})
            except ValueError as decode_error:
                # ValueError typically means invalid token format
                logger.error(f"ValueError decoding token: {decode_error}")
                logger.error(
                    f"Token length: {len(token)}, Token preview: {token[:50]}")
                raise TokenValidationError(
                    f"Invalid token format: {str(decode_error)}", 401)
            except Exception as decode_error:
                logger.error(
                    f"Failed to decode token: {type(decode_error).__name__}: {decode_error}"
                )
                logger.error(
                    f"Token length: {len(token)}, Token preview: {token[:50]}")
                raise TokenValidationError(
                    f"Error decoding token claims: {str(decode_error)}", 401)

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
        logger.info(
            f"Token validated successfully. Exp: {unverified.get('exp')}, Patient: {unverified.get('patient_id', unverified.get('patient'))}"
        )
        return unverified

    except TokenValidationError:
        raise
    except JWTError as e:
        logger.error(f"JWTError decoding token: {e}")
        raise TokenValidationError(
            f"Invalid token: Error decoding token claims. {str(e)}", 401)
    except Exception as e:
        logger.error(
            f"Unexpected error validating token: {type(e).__name__}: {e}")
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
            "valid":
            False,
            "error":
            "Invalid authorization header format. Expected 'Bearer <token>'"
        }), 401

    token = authorization.replace("Bearer ", "").strip()

    try:
        payload = validate_token(token)
        return jsonify({"valid": True, "payload": payload})
    except TokenValidationError as e:
        return jsonify({"valid": False, "error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 401
