"""
FHIR API proxy endpoints
Proxies FHIR requests after token validation
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import InternalServerError, ServiceUnavailable
import os
import logging
from fhirclient import client
from fhirclient.models import patient, observation

logger = logging.getLogger(__name__)

bp = Blueprint("fhir", __name__)

# Get FHIR server base URL from environment
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "")


def extract_token_from_header(authorization: str) -> str:
    """
    Extract and validate token from Authorization header

    Args:
        authorization: Authorization header value

    Returns:
        str: Cleaned token

    Raises:
        Unauthorized: If token is missing or invalid
    """
    if not authorization:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Authorization header missing")

    if not authorization.startswith("Bearer "):
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Invalid authorization header format")

    # Extract token - take everything after "Bearer " and before any whitespace or newline
    token = authorization.replace("Bearer ", "", 1).strip()

    # Remove any trailing content after the token (in case of concatenation)
    # A JWT token should be the first "word" after Bearer
    if token:
        token = token.split()[0] if token.split() else token
    else:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Token is empty after extraction")

    # Validate token exists and has minimum length
    if not token or len(token) < 10:
        logger.error(
            f"Token is empty or too short: length={len(token) if token else 0}"
        )
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized("Invalid token: token is empty or too short")

    return token


def get_fhir_server(access_token: str = None):
    """
    Create a FHIR server instance configured with the base URL and access token

    Args:
        access_token: OAuth access token

    Returns:
        client.FHIRServer: Configured FHIR server
    """
    if not FHIR_BASE_URL:
        raise InternalServerError("FHIR_BASE_URL not configured")

    settings = {'app_id': 'smart-on-fhir-tutorial', 'api_base': FHIR_BASE_URL}

    # Create client and get server instance
    fhir_client = client.FHIRClient(settings=settings)
    server = fhir_client.server

    # Set bearer token in headers if provided
    if access_token:
        # fhirclient's server uses requests.Session internally
        # We can set default headers for bearer token authentication
        server.session.headers.update(
            {'Authorization': f'Bearer {access_token}'})

    return server


def get_fhir_resource(resource_type: str,
                      resource_id: str = None,
                      access_token: str = None,
                      query_params: dict = None) -> dict:
    """
    Make a request to the FHIR server using fhirclient

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

    try:
        # Get configured FHIR server
        server = get_fhir_server(access_token)

        # Build resource reference
        if resource_id:
            resource_ref = f"{resource_type}/{resource_id}"
        else:
            resource_ref = resource_type

        # Make request using fhirclient
        if resource_id:
            # Read a specific resource using fhirclient models
            if resource_type == "Patient":
                patient_obj = patient.Patient.read(resource_id, server)
                logger.warning(f"FHIR read Patient/{resource_id}")
                return patient_obj.as_json()
            elif resource_type == "Observation":
                obs_obj = observation.Observation.read(resource_id, server)
                logger.warning(f"FHIR read Observation/{resource_id}")
                return obs_obj.as_json()
            else:
                # Generic read using server.request_json
                url = f"{resource_ref}"
                response = server.request_json(url)
                logger.warning(
                    f"FHIR read {resource_ref}: {response.get('resourceType', 'Unknown')}"
                )
                return response
        else:
            # Search for resources
            search_params = query_params or {}

            # Use fhirclient's search methods
            # fhirclient's where() method accepts keyword arguments, not a dict
            if resource_type == "Patient":
                # Convert dict to keyword arguments
                results = patient.Patient.where(
                    **search_params).perform_resources(server)
                # Convert to Bundle format
                bundle = {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": len(results),
                    "entry": [{
                        "resource": r.as_json()
                    } for r in results]
                }
                logger.warning(
                    f"FHIR search returned {len(results)} Patient resources")
                return bundle
            elif resource_type == "Observation":
                # Convert dict to keyword arguments
                results = observation.Observation.where(
                    struct=search_params).perform_resources(server)
                # Convert to Bundle format
                bundle = {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": len(results),
                    "entry": [{
                        "resource": r.as_json()
                    } for r in results]
                }
                logger.warning(
                    f"FHIR search returned {len(results)} Observation resources"
                )
                return bundle
            else:
                # Generic search using direct request
                url = f"{resource_ref}"
                if search_params:
                    from urllib.parse import urlencode
                    url += "?" + urlencode(search_params)

                response = server.request_json(url)
                logger.warning(
                    f"FHIR search {resource_ref}: {response.get('resourceType', 'Unknown')}"
                )
                return response

    except Exception as e:
        logger.error(f"FHIR client error: {type(e).__name__}: {str(e)}")
        # Check if it's an HTTP error from requests
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            from werkzeug.exceptions import HTTPException
            error_text = e.response.text if hasattr(e.response,
                                                    'text') else str(e)
            raise HTTPException(description=f"FHIR server error: {error_text}",
                                response=e.response)
        else:
            raise ServiceUnavailable(
                f"Failed to connect to FHIR server: {str(e)}")


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
    logger.warning(
        f"GET /api/fhir/Patient/{patient_id} - Authorization header present: {bool(authorization)}"
    )

    # Extract and validate token
    token = extract_token_from_header(authorization)

    # Get patient resource
    logger.warning(f"Getting patient resource: {patient_id}")
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

    # Extract and validate token
    token = extract_token_from_header(authorization)

    # Build query parameters from request
    query_params = {}
    patient = request.args.get("patient")
    code = request.args.get("code")
    _count = request.args.get("_count")
    logger.warning(
        f"Query parameters: patient={patient}, code={code}, _count={_count}")
    logger.warning(f"Final query_params: {query_params}")
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

    # Extract and validate token
    token = extract_token_from_header(authorization)

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
