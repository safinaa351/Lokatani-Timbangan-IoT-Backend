from flask import Blueprint, request, jsonify
import logging
from app.validators import validate_json_request, handle_api_exception, validate_api_key
from app.services.iot_service import process_weight_from_device, update_device_status
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