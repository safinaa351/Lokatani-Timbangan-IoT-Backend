from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import logging
from app.validators import (
    validate_uploaded_file, validate_json_request, handle_api_exception,
    validate_numeric, validate_string
)
from app.jwt.jwt_middleware import token_required  # Import JWT middleware

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
        "version": "1.0.0"}), 200

@routes.route('/api/batch/initiate', methods=['POST'])
@token_required  # Protect with JWT
@validate_json_request(required_fields=['user_id'])
@handle_api_exception
def initiate_batch_tracking():
    data = request.json
    logger.info(f"Batch initiation request: {data}")
    
    # Validate that the authenticated user matches the user_id in the request
    if request.user.get('user_id') != data.get('user_id') and request.user.get('role') != 'admin':
        logger.warning(f"User {request.user.get('user_id')} attempted to initiate batch for {data.get('user_id')}")
        return jsonify({
            "status": "error", 
            "message": "You can only initiate batches for your own account"
        }), 403
    
    # Validate user_id
    error = validate_string(data['user_id'], 'User ID')
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    # Initiate batch
    batch_info = initiate_batch(data)
    
    logger.info(f"Batch initiated: {batch_info}")
    return jsonify(batch_info), 200

@routes.route('/api/batch/complete', methods=['POST'])
@token_required  # Protect with JWT
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
@token_required  # Protect with JWT
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
@token_required  # Protect with JWT
@handle_api_exception
def handle_rompes_weighing():
    logger.info("Rompes weighing request received")
    
    # Validate that we have the required data
    if 'file' not in request.files:
        logger.warning("No image file in request")
        return jsonify({
            "status": "error",
            "message": "No image file provided"
        }), 400
        
    for field in ['weight', 'user_id']:
        if field not in request.form:
            logger.warning(f"No {field} in request")
            return jsonify({
                "status": "error",
                "message": f"{field.replace('_', ' ').title()} is required"
            }), 400
    
    # Extract data
    file = request.files['file']
    user_id = request.form.get('user_id')
    notes = request.form.get('notes', '')
    
    # Verify user is processing for their own account
    if request.user.get('user_id') != user_id and request.user.get('role') != 'admin':
        logger.warning(f"User {request.user.get('user_id')} attempted rompes weighing for {user_id}")
        return jsonify({
            "status": "error", 
            "message": "You can only process weighing for your own account"
        }), 403
    
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
    except ValueError as e:
        logger.warning(f"Weight validation failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Invalid weight value: {str(e)}"
        }), 400
    
    # Process rompes weighing
    logger.info(f"Processing rompes weighing. Weight: {weight}g, User: {user_id}")
    safe_filename = secure_filename(file.filename)
    result = process_rompes_weighing(file, safe_filename, weight, user_id, notes)
    
    logger.info(f"Rompes weighing processed: {result}")
    return jsonify(result), 200

@routes.route('/api/batches/history', methods=['GET'])
@token_required  # Protect with JWT
@handle_api_exception
def get_user_batches():
    user_id = request.args.get('user_id')
    logger.info(f"Fetching batch history for user: {user_id}")
    
    if not user_id:
        logger.warning("Missing user_id in batch history request")
        return jsonify({"status": "error", "message": "User ID is required"}), 400
    
    # Verify user is accessing their own batches
    if request.user.get('user_id') != user_id and request.user.get('role') != 'admin':
        logger.warning(f"User {request.user.get('user_id')} attempted to access batches for {user_id}")
        return jsonify({
            "status": "error", 
            "message": "You can only view your own batches"
        }), 403
        
    batches = get_user_batch_history(user_id)
    logger.info(f"Retrieved {len(batches)} batches for user {user_id}")
    
    return jsonify({"status": "success", "batches": batches}), 200

@routes.route('/api/batches/<batch_id>', methods=['GET'])
@token_required  # Protect with JWT
@handle_api_exception
def get_batch_details(batch_id):
    logger.info(f"Fetching details for batch: {batch_id}")
    
    if not batch_id:
        return jsonify({"status": "error", "message": "Batch ID is required"}), 400
        
    batch_details = get_batch_detail(batch_id)
    
    if batch_details.get('status') == 'error':
        logger.warning(f"Batch details request failed: {batch_details.get('message')}")
        return jsonify(batch_details), 404
    
    # Verify user owns the batch or is admin
    if batch_details.get('batch', {}).get('user_id') != request.user.get('user_id') and request.user.get('role') != 'admin':
        logger.warning(f"User {request.user.get('user_id')} attempted to access batch {batch_id} belonging to another user")
        return jsonify({
            "status": "error", 
            "message": "You can only view your own batches"
        }), 403
        
    logger.info(f"Retrieved details for batch: {batch_id}")
    return jsonify(batch_details), 200