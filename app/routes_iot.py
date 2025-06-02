from flask import Blueprint, request, jsonify
import logging
from app.validators import validate_json_request, handle_api_exception, validate_api_key
from app.services.iot_service import (
    process_weight_from_device,
    get_active_weighing_session,
    update_device_status
)

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

@iot_routes.route('/api/iot/active-session', methods=['GET'])
@limiter.limit("500 per hour; 5000 per day")
@validate_api_key('IOT_API_KEY')
@handle_api_exception
def handle_get_active_batch():
    """Requesting the most recent active weighing session (product or rompes)"""
    active_session = get_active_weighing_session()
    
    if not active_session:
        logger.info("No active weighing sessions found")
        return jsonify({
            "status": "not_found",
            "message": "No active weighing session found"
        }), 404
    
    logger.info(f"Active session found: {active_session['session_id']} (type: {active_session['session_type']})")

    return jsonify({
        "status": "active session found",
        "batch": {
            "session_id": active_session['session_id'],  # This will have prefix: prod_ or rompes_
            "session_type": active_session['session_type'],
            "status": active_session.get('status')
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