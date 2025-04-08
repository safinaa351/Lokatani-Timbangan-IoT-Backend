from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import logging
from app.validators import (
    validate_uploaded_file, validate_json_request, handle_api_exception,
    validate_numeric, validate_string
)

from app.services.service import (
    upload_image,
    initiate_batch, 
    complete_batch, 
    detect_weight, 
    stabilize_weight,
    identify_vegetable,
    process_rompes_weighing
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

@routes.route('/api/weight/detection', methods=['POST'])
@validate_json_request(required_fields=['current_weight'])
@handle_api_exception
def handle_weight_detection():
    data = request.json
    logger.info(f"Weight detection received: {data}")
    
    # Validate weight value
    error = validate_numeric(data['current_weight'], 'Weight', min_value=0)
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    # Process weight detection
    result = detect_weight(data['current_weight'])
    
    logger.info(f"Weight detection processed: {result}")
    return jsonify(result), 200

@routes.route('/api/weight/stabilized', methods=['POST'])
@validate_json_request(required_fields=['stabilized_weight', 'batch_id'])
@handle_api_exception
def handle_weight_stabilization():
    data = request.json
    logger.info(f"Stabilized weight received: {data}")
    
    # Validate weight value and batch_id
    error = validate_numeric(data['stabilized_weight'], 'Stabilized weight', min_value=0)
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    error = validate_string(data['batch_id'], 'Batch ID')
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    # Save stabilized weight
    result = stabilize_weight(data)
    
    logger.info(f"Stabilized weight processed: {result}")
    return jsonify(result), 200

@routes.route('/api/batch/initiate', methods=['POST'])
@validate_json_request(required_fields=['user_id'])
@handle_api_exception
def initiate_batch_tracking():
    data = request.json
    logger.info(f"Batch initiation request: {data}")
    
    # Validate user_id
    error = validate_string(data['user_id'], 'User ID')
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    # Initiate batch
    batch_info = initiate_batch(data)
    
    logger.info(f"Batch initiated: {batch_info}")
    return jsonify(batch_info), 200

@routes.route('/api/batch/complete', methods=['POST'])
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

#ROMPESSSSSSSSSSSSSSSSS
@routes.route('/api/rompes/process', methods=['POST'])
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