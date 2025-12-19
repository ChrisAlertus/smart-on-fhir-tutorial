"""
FHIR API proxy endpoints
Proxies FHIR requests after token validation
"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import InternalServerError, ServiceUnavailable
import requests
import os
try:
    from backend.auth import validate_token, TokenValidationError
except ImportError:
    from auth import validate_token, TokenValidationError

bp = Blueprint("fhir", __name__)

# Get FHIR server base URL from environment
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "")

def get_fhir_resource(
    resource_type: str,
    resource_id: str = None,
    access_token: str = None,
    query_params: dict = None
) -> dict:
    """
    Make a request to the FHIR server

    Args:
        resource_type: FHIR resource type (e.g., "Patient", "Observation")
        resource_id: Optional resource ID
        access_token: OAuth access token
        query_params: Optional query parameters

    Returns:
        dict: FHIR resource response
    """
    if not FHIR_BASE_URL:
        raise InternalServerError("FHIR_BASE_URL not configured")

    # Build URL
    if resource_id:
        url = f"{FHIR_BASE_URL}/{resource_type}/{resource_id}"
    else:
        url = f"{FHIR_BASE_URL}/{resource_type}"

    # Prepare headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    # Make request
    try:
        response = requests.get(
            url,
            headers=headers,
            params=query_params,
            timeout=30.0,
            verify=True
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        from werkzeug.exceptions import HTTPException
        raise HTTPException(description=f"FHIR server error: {e.response.text}", response=e.response)
    except requests.exceptions.RequestException as e:
        raise ServiceUnavailable(f"Failed to connect to FHIR server: {str(e)}")

@bp.route("/Patient/<patient_id>", methods=["GET"])
def get_patient(patient_id: str):
    """
    Get patient resource by ID

    Args:
        patient_id: Patient ID

    Returns:
        dict: Patient resource
    """
    authorization = request.headers.get("Authorization")

    if not authorization:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Authorization header missing")

    if not authorization.startswith("Bearer "):
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Invalid authorization header format")

    token = authorization.replace("Bearer ", "").strip()

    # Validate token
    try:
        validate_token(token)
    except TokenValidationError as e:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized(e.message)

    # Get patient resource
    return jsonify(get_fhir_resource("Patient", patient_id, token))

@bp.route("/Observation", methods=["GET"])
def get_observations():
    """
    Get observation resources with optional filters

    Query Parameters:
        patient: Patient ID filter
        code: Observation code filter (LOINC format)
        _count: Maximum number of results

    Returns:
        dict: Bundle of Observation resources
    """
    authorization = request.headers.get("Authorization")

    if not authorization:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Authorization header missing")

    if not authorization.startswith("Bearer "):
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Invalid authorization header format")

    token = authorization.replace("Bearer ", "").strip()

    # Validate token
    try:
        validate_token(token)
    except TokenValidationError as e:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized(e.message)

    # Build query parameters from request
    query_params = {}
    patient = request.args.get("patient")
    code = request.args.get("code")
    _count = request.args.get("_count")

    if patient:
        query_params["patient"] = patient
    if code:
        query_params["code"] = code
    if _count:
        query_params["_count"] = _count

    # Get all query parameters from the request
    for key, value in request.args.items():
        if key not in ["patient", "code", "_count"]:
            query_params[key] = value

    # Get observations
    return jsonify(get_fhir_resource("Observation", None, token, query_params))

@bp.route("/Patient", methods=["GET"])
def search_patients():
    """
    Search for patients with optional filters

    Query Parameters:
        identifier: Patient identifier filter
        name: Patient name filter
        _count: Maximum number of results

    Returns:
        dict: Bundle of Patient resources
    """
    authorization = request.headers.get("Authorization")

    if not authorization:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Authorization header missing")

    if not authorization.startswith("Bearer "):
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Invalid authorization header format")

    token = authorization.replace("Bearer ", "").strip()

    # Validate token
    try:
        validate_token(token)
    except TokenValidationError as e:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized(e.message)

    # Build query parameters
    query_params = {}
    identifier = request.args.get("identifier")
    name = request.args.get("name")
    _count = request.args.get("_count")

    if identifier:
        query_params["identifier"] = identifier
    if name:
        query_params["name"] = name
    if _count:
        query_params["_count"] = _count

    # Get all query parameters from the request
    for key, value in request.args.items():
        if key not in ["identifier", "name", "_count"]:
            query_params[key] = value

    # Search patients
    return jsonify(get_fhir_resource("Patient", None, token, query_params))
