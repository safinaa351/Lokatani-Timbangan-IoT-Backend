from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import logging
from app.services.service import (
    upload_image,
    initiate_batch, 
    complete_batch, 
    detect_weight, 
    stabilize_weight,
    identify_vegetable
)

routes = Blueprint('routes', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image(file):
    try:
        Image.open(file).verify()
        file.seek(0)
        return True
    except Exception:
        return False
    
def validate_uploaded_file(file):
    if file.filename == '':
        return "No selected file"
    if not allowed_file(file.filename):
        return "Invalid file extension"
    if not is_image(file):
        return "Invalid image file"
    return None

@routes.route('/')
def home():
    """Basic health check endpoint"""
    logger.info("Home endpoint accessed")
    return jsonify({"status": "Backend is running", "message": "IoT Vegetable Weighing System"}), 200

@routes.route('/api/weight/detection', methods=['POST'])
def handle_weight_detection():
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
    if 'file' not in request.files:
        logger.warning("No file part in the request")
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    batch_id = request.form.get('batch_id')

    error = validate_uploaded_file(file)
    if error:
        logger.warning(f"File validation failed: {error}")
        return jsonify({"error": error}), 400

    try:
        safe_filename = secure_filename(file.filename)
        image_url = upload_image(file, safe_filename)
        identification_result = identify_vegetable(image_url, batch_id)

        logger.info(f"Vegetable identification result: {identification_result}")
        return jsonify(identification_result), 200

    except Exception as e:
        logger.error(f"Error in vegetable identification: {str(e)}")
        return jsonify({"error": str(e)}), 500