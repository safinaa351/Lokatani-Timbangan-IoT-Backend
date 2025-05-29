from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import logging
from app.validators import (
    validate_uploaded_file, validate_json_request, handle_api_exception,
    validate_numeric, validate_string
)
from app.firebase_auth.firebase_middleware import firebase_token_required

from app.services.service import (
    upload_image,
    initiate_batch, 
    complete_batch,
    process_rompes_weighing,
    identify_vegetable,
    get_user_batch_history,
    get_batch_detail
)

routes = Blueprint('routes', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@routes.route('/')
def home():
    """Basic health check endpoint"""
    logger.info("Home endpoint accessed")
    return jsonify({
        "status": "success",
        "message": "Backend is running",
        "service": "IoT Vegetable Weighing System",
        "version": "2.0.0",
        "auth": "Firebase Authentication"}), 200

@routes.route('/api/batch/initiate', methods=['POST'])
@firebase_token_required
@handle_api_exception
def initiate_batch_tracking():
    data = request.json or {}
    logger.info(f"Batch initiation request: {data}")
    
    # Get user_id directly from the authenticated token
    authenticated_user_id = request.user.get('firebase_uid')  # This is the Firebase localId
    
    if not authenticated_user_id:
         # This shouldn't happen if firebase_token_required works correctly
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500
    
    logger.info(f"Authenticated user ID (firebase_uid): {authenticated_user_id}")

    # Force the user_id to be the authenticated user's ID for security
    data['user_id'] = authenticated_user_id
    
    # Initiate batch
    batch_info = initiate_batch(data)
    
    logger.info(f"Batch initiated: {batch_info}")
    return jsonify(batch_info), 200

@routes.route('/api/batch/complete', methods=['POST'])
@firebase_token_required
@validate_json_request(required_fields=['batch_id'])
@handle_api_exception
def finalize_batch_tracking():
    data = request.json
    logger.info(f"Batch completion request: {data}")
    
    # Validate batch_id
    error = validate_string(data['batch_id'], 'Batch ID')
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    # Complete batch
    batch_result = complete_batch(data)
    
    logger.info(f"Batch completed: {batch_result}")
    return jsonify(batch_result), 200

@routes.route('/api/ml/identify-vegetable', methods=['POST'])
@firebase_token_required
@handle_api_exception
def process_vegetable_identification():
    logger.info("Vegetable identification request received")
    
    if 'file' not in request.files:
        logger.warning("No file part in the request")
        return jsonify({
            "status": "error",
            "message": "No file part in the request"
        }), 400

    file = request.files['file']
    batch_id = request.form.get('batch_id')
    
    # Validate batch_id if provided
    if batch_id is not None:
        error = validate_string(batch_id, 'Batch ID')
        if error:
            return jsonify({"status": "error", "message": error}), 400

    # Validate image file
    error = validate_uploaded_file(file)
    if error:
        logger.warning(f"File validation failed: {error}")
        return jsonify({"status": "error", "message": error}), 400

    # Process image and identify vegetable
    safe_filename = secure_filename(file.filename)
    logger.info(f"Processing image: {safe_filename}")
    
    image_url = upload_image(file, safe_filename)
    identification_result = identify_vegetable(image_url, batch_id)

    logger.info(f"Vegetable identification result: {identification_result}")
    return jsonify(identification_result), 200

@routes.route('/api/rompes/process', methods=['POST'])
@firebase_token_required
@handle_api_exception
def handle_rompes_weighing():
    logger.info("Rompes weighing request received")
    
    # Validate that we have the required data (file & weight)
    required_form_fields = ['weight']
    for field in required_form_fields:
        if field not in request.form:
            logger.warning(f"No {field} in request form data")
            return jsonify({
                "status": "error",
                "message": f"{field.replace('_', ' ').title()} is required"
            }), 400

    if 'file' not in request.files:
        logger.warning("No image file in request")
        return jsonify({
            "status": "error",
            "message": "No image file provided"
        }), 400
    
    # Extract data
    file = request.files['file']
    notes = request.form.get('notes', '')
    
    # Get the authenticated user's ID from the token - this is the user performing the action
    authenticated_user_id = request.user.get('firebase_uid')
    if not authenticated_user_id:
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500

    logger.info(f"Rompes weighing initiated by user: {authenticated_user_id}")
    
    # Validate file
    error = validate_uploaded_file(file)
    if error:
        logger.warning(f"File validation failed: {error}")
        return jsonify({"status": "error", "message": error}), 400
    
    # Validate weight
    try:
        weight = float(request.form.get('weight'))
        if weight <= 0:
            raise ValueError("Weight must be greater than zero")
    except (ValueError, TypeError) as e:
        logger.warning(f"Weight validation failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Invalid weight value: {str(e)}"
        }), 400
    
    # Process rompes weighing
    logger.info(f"Processing rompes weighing. Weight: {weight}g, User: {authenticated_user_id}")
    safe_filename = secure_filename(file.filename)
    result = process_rompes_weighing(file, safe_filename, weight, authenticated_user_id, notes)
    
    logger.info(f"Rompes weighing processed: {result}")
    return jsonify(result), 200

@routes.route('/api/batches/history', methods=['GET'])
@firebase_token_required
@handle_api_exception
def get_user_batches():
    logger.info(f"Fetching batch history")
    
    # Get the authenticated user's ID from the token - fetching history for this user
    authenticated_user_id = request.user.get('firebase_uid')
    if not authenticated_user_id:
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500

    logger.info(f"Fetching batch history for user: {authenticated_user_id}")
        
    batches = get_user_batch_history(authenticated_user_id)
    logger.info(f"Retrieved {len(batches)} batches for user {authenticated_user_id}")
    
    return jsonify({"status": "success", "batches": batches}), 200

@routes.route('/api/batches/<batch_id>', methods=['GET'])
@firebase_token_required
@handle_api_exception
def get_batch_details(batch_id):
    logger.info(f"Fetching details for batch: {batch_id}")
    
    if not batch_id:
        return jsonify({"status": "error", "message": "Batch ID is required"}), 400
    
    # Get the authenticated user's ID from the token
    authenticated_user_id = request.user.get('firebase_uid')
    if not authenticated_user_id:
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500

    batch_details_result = get_batch_detail(batch_id)
    # Check if batch exists and retrieve batch owner ID
    batch_data = batch_details_result.get('batch')
    if batch_details_result.get('status') == 'error' or not batch_data:
        logger.warning(f"Batch {batch_id} not found or error retrieving details: {batch_details_result.get('message', 'Unknown error')}")
    
    # Verify user owns the batch or is admin
    if batch_owner_id != authenticated_user_id and request.user.get('role') != 'admin':
        logger.warning(f"User {authenticated_user_id} attempted to access batch {batch_id} belonging to user {batch_owner_id}")
        return jsonify({
            "status": "error",
            "message": "You can only view your own batches or you are not authorized"
        }), 403
        
    logger.info(f"Retrieved details for batch: {batch_id}")
    return jsonify({"status": "success", "batch": batch_data}), 200