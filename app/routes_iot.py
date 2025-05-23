from flask import Blueprint, request, jsonify
import logging
from app.validators import validate_json_request, handle_api_exception, validate_api_key
from app.services.iot_service import process_weight_from_device, update_device_status, get_active_batch
from app import limiter

iot_routes = Blueprint('iot_routes', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@iot_routes.route('/api/iot/weight', methods=['POST'])
@limiter.limit("500 per hour; 5000 per day") # custom rate limit for iot
@validate_api_key('IOT_API_KEY')
@validate_json_request(required_fields=['device_id', 'weight'])
@handle_api_exception
def handle_iot_weight():
    data = request.json
    logger.info(f"IoT weight data received: {data}")
    
    # Process the weight data
    result = process_weight_from_device(data)
    
    return jsonify(result), 200

@iot_routes.route('/api/iot/active-batch', methods=['GET'])
@limiter.limit("500 per hour; 5000 per day")
@validate_api_key('IOT_API_KEY')
@handle_api_exception
def handle_get_active_batch():
    """Get the most recent active batch that hasn't been completed"""
    active_batch = get_active_batch()
    
    if not active_batch:
        return jsonify({
            "status": "not_found",
            "message": "No active batch found"
        }), 404
    
    return jsonify({
        "status": "newest batch ID found",
        "batch": {
            "batch_id": active_batch['batch_id'],
            "status": active_batch.get('status')
            #"created_at": active_batch.get('created_at'),
            #"user_id": active_batch.get('user_id'),
            #"total_weight": active_batch.get('total_weight', 0)
        }
    }), 200

@iot_routes.route('/api/iot/status', methods=['POST'])
@limiter.limit("500 per hour; 5000 per day")
@validate_json_request(required_fields=['device_id'])
@handle_api_exception
def handle_device_status():
    data = request.json
    logger.info(f"IoT device status update received: {data}")
    
    # Process the status update
    result = update_device_status(data.get('device_id'), data)
    
    return jsonify(result), 200