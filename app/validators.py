from flask import request, jsonify
import logging
from PIL import Image
import json
import functools
import os


# Setup logging
logger = logging.getLogger(__name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image(file):
    """Verify that the file is a valid image"""
    try:
        Image.open(file).verify()
        file.seek(0)  # Reset file pointer
        return True
    except Exception as e:
        logger.error(f"Image validation error: {str(e)}")
        file.seek(0)  # Ensure file pointer is reset even on error
        return False
    
def validate_uploaded_file(file):
    """Validate uploaded file"""
    if file.filename == '':
        return "No selected file"
    if not allowed_file(file.filename):
        return "Invalid file extension. Allowed extensions: png, jpg, jpeg"
    if not is_image(file):
        return "Invalid image file or corrupted image data"
    return None

def validate_json_payload(payload, required_fields):
    """Validate if JSON payload contains all required fields"""
    if not payload:
        return "Missing JSON payload"
    
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    
    return None

def validate_numeric(value, field_name, min_value=None):
    """Validate that value is numeric and optionally above minimum"""
    if not isinstance(value, (int, float)):
        return f"{field_name} must be a number"
    if min_value is not None and value <= min_value:
        return f"{field_name} must be greater than {min_value}"
    return None

def validate_string(value, field_name):
    """Validate that value is a non-empty string"""
    if not isinstance(value, str) or not value.strip():
        return f"{field_name} must be a non-empty string"
    return None

# Decorator for JSON API endpoint validation
def validate_json_request(required_fields=None):
    """Decorator for validating JSON requests"""
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Check Content-Type
            if not request.is_json:
                logger.warning(f"Request to {request.path} has invalid Content-Type")
                return jsonify({
                    "status": "error",
                    "message": "Content-Type must be application/json"
                }), 415
            
            try:
                data = request.json
                
                # Validate required fields if specified
                if required_fields:
                    error = validate_json_payload(data, required_fields)
                    if error:
                        logger.warning(f"Validation error in {request.path}: {error}")
                        return jsonify({"status": "error", "message": error}), 400
                
                # Pass data to the original function
                return f(*args, **kwargs)
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON format in request to {request.path}")
                return jsonify({
                    "status": "error",
                    "message": "Invalid JSON format"
                }), 400
                
        return wrapper
    return decorator

# Exception handler for API routes
def handle_api_exception(f):
    """Decorator for handling exceptions in API routes"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "Internal server error",
                "details": str(e)
            }), 500
    return wrapper

### checks API KEY of IoT devices ###
def validate_api_key(api_key_name):
    """Decorator for validating API key in request header"""
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            expected_key = os.getenv(api_key_name)
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning(f"Missing or invalid Authorization header in request to {request.path}")
                return jsonify({
                    "status": "error",
                    "message": "Authentication required"
                }), 401
                
            provided_key = auth_header.split('Bearer ')[1]
            if provided_key != expected_key:
                logger.warning(f"Invalid API key in request to {request.path}")
                return jsonify({
                    "status": "error",
                    "message": "Invalid authentication"
                }), 401
                
            return f(*args, **kwargs)
        return wrapper
    return decorator