"""
Token validation module
Validates JWT tokens from frontend requests
"""
from flask import Blueprint

bp = Blueprint("auth", __name__)


class TokenValidationError(Exception):
    """Custom exception for token validation errors"""

    def __init__(self, message, status_code=401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
