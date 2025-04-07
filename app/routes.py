from flask import Blueprint, request, jsonify
import imghdr
import logging
from app.services.service import (
    upload_image, 
    save_weight, 
    initiate_batch, 
    complete_batch, 
    detect_weight, 
    stabilize_weight,
    identify_vegetable
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

routes = Blueprint('routes', __name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    """Cek apakah file memiliki ekstensi gambar yang valid"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@routes.route('/')
def home():
    """Basic health check endpoint"""
    logger.info("Home endpoint accessed")
    return jsonify({"status": "Backend is running", "message": "IoT Vegetable Weighing System"}), 200

@routes.route('/api/weight/detection', methods=['POST'])
def handle_weight_detection():
    """
    Handle initial weight detection from IoT scale
    
    Expected JSON payload:
    {
        "scale_id": "unique_scale_identifier",
        "current_weight": float,
        "unit": "grams"
    }
    """
    try:
        data = request.json
        logger.info(f"Weight detection received: {data}")
        
        # Validate input
        if not data or 'current_weight' not in data:
            logger.warning("Invalid weight detection payload")
            return jsonify({"error": "Invalid payload"}), 400
        
        # Process weight detection
        result = detect_weight(data)
        
        logger.info(f"Weight detection processed: {result}")
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error in weight detection: {str(e)}")
        return jsonify({"error": str(e)}), 500

@routes.route('/api/weight/stabilized', methods=['POST'])
def handle_weight_stabilization():
    """
    Handle stabilized weight from IoT scale
    
    Expected JSON payload:
    {
        "batch_id": "unique_batch_identifier",
        "stabilized_weight": float,
        "scale_id": "unique_scale_identifier"
    }
    """
    try:
        data = request.json
        logger.info(f"Stabilized weight received: {data}")
        
        # Validate input
        if not data or 'stabilized_weight' not in data or 'batch_id' not in data:
            logger.warning("Invalid stabilized weight payload")
            return jsonify({"error": "Invalid payload"}), 400
        
        # Save stabilized weight
        result = stabilize_weight(data)
        
        logger.info(f"Stabilized weight processed: {result}")
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error in weight stabilization: {str(e)}")
        return jsonify({"error": str(e)}), 500

@routes.route('/api/batch/initiate', methods=['POST'])
def initiate_batch_tracking():
    """
    Initiate a new batch tracking session
    
    Expected JSON payload:
    {
        "user_id": "unique_user_identifier",
        "scale_id": "unique_scale_identifier"
    }
    """
    try:
        data = request.json
        logger.info(f"Batch initiation request: {data}")
        
        # Validate input
        if not data or 'user_id' not in data:
            logger.warning("Invalid batch initiation payload")
            return jsonify({"error": "Invalid payload"}), 400
        
        # Initiate batch
        batch_info = initiate_batch(data)
        
        logger.info(f"Batch initiated: {batch_info}")
        return jsonify(batch_info), 200
    
    except Exception as e:
        logger.error(f"Error initiating batch: {str(e)}")
        return jsonify({"error": str(e)}), 500

@routes.route('/api/batch/complete', methods=['POST'])
def finalize_batch_tracking():
    """
    Complete and finalize a batch tracking session
    
    Expected JSON payload:
    {
        "batch_id": "unique_batch_identifier",
        "total_weight": float,
        "vegetable_type": "string"
    }
    """
    try:
        data = request.json
        logger.info(f"Batch completion request: {data}")
        
        # Validate input
        if not data or 'batch_id' not in data:
            logger.warning("Invalid batch completion payload")
            return jsonify({"error": "Invalid payload"}), 400
        
        # Complete batch
        batch_result = complete_batch(data)
        
        logger.info(f"Batch completed: {batch_result}")
        return jsonify(batch_result), 200
    
    except Exception as e:
        logger.error(f"Error completing batch: {str(e)}")
        return jsonify({"error": str(e)}), 500

@routes.route('/api/ml/identify-vegetable', methods=['POST'])
def process_vegetable_identification():
    """
    Process vegetable identification from uploaded image
    
    Expects multipart form-data with:
    - file: Image file
    - batch_id: Optional batch identifier
    """
    if 'file' not in request.files:
        logger.warning("No file part in the request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    batch_id = request.form.get('batch_id')

    if file.filename == '':
        logger.warning("No selected file")
        return jsonify({"error": "No selected file"}), 400

    # Validate file type
    if not allowed_file(file.filename):
        logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({"error": "Invalid file type"}), 400

    # Additional MIME type check
    file_type = imghdr.what(file)
    if file_type not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid file content: {file_type}")
        return jsonify({"error": "Invalid file content"}), 400

    try:
        # Upload image and process identification
        image_url = upload_image(file, file.filename)
        identification_result = identify_vegetable(image_url, batch_id)
        
        logger.info(f"Vegetable identification result: {identification_result}")
        return jsonify(identification_result), 200
    
    except Exception as e:
        logger.error(f"Error in vegetable identification: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Deprecated endpoints (kept for backwards compatibility)
@routes.route('/upload', methods=['POST'])
def legacy_upload_file():
    """Legacy image upload endpoint - will be deprecated"""
    logger.warning("Using deprecated upload endpoint")
    return process_vegetable_identification()

@routes.route('/upload_with_weight', methods=['POST'])
def legacy_upload_with_weight():
    """Legacy upload with weight endpoint - will be deprecated"""
    logger.warning("Using deprecated upload with weight endpoint")
    return process_vegetable_identification()