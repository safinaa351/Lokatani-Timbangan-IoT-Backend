from google.cloud import firestore
from datetime import datetime
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firestore client
firestore_client = firestore.Client()

# Constants
DEVICE_COLLECTION = "iot_devices"
BATCH_COLLECTION = "vegetable_batches"
WEIGHTS_SUBCOLLECTION = "weights"

def update_device_status(device_id, status_data):
    """Update the status of an IoT device"""
    try:
        device_ref = firestore_client.collection(DEVICE_COLLECTION).document(device_id)
        status_data["last_seen"] = datetime.utcnow()
        
        device_ref.set(status_data, merge=True)
        
        logger.info(f"Updated status for device {device_id}")
        return {
            "status": "success",
            "device_id": device_id,
            "message": "Device status updated"
        }
        
    except Exception as e:
        logger.error(f"Error updating device status: {str(e)}")
        raise

#UNIFIED WEIGHING SESSION TESTING 
def get_active_weighing_session():
    """Get any active weighing session (product or rompes)"""
    try:
        active_sessions = []
        
        # Check for active product sessions
        product_ref = firestore_client.collection(BATCH_COLLECTION)
        product_query = product_ref.where('status', '==', 'in_progress')\
                               .order_by('created_at', direction=firestore.Query.DESCENDING)
        
        for batch in product_query.stream():
            session_data = batch.to_dict()
            session_data['session_id'] = batch.id
            session_data['session_type'] = 'product'
            active_sessions.append(session_data)
        
        # Check for active rompes sessions
        rompes_ref = firestore_client.collection('rompes_batches')
        rompes_query = rompes_ref.where('status', '==', 'in_progress')\
                                .order_by('created_at', direction=firestore.Query.DESCENDING)
        
        for batch in rompes_query.stream():
            session_data = batch.to_dict()
            session_data['session_id'] = batch.id
            session_data['session_type'] = 'rompes'
            active_sessions.append(session_data)
        
        if not active_sessions:
            logger.info("No active weighing sessions found")
            return None
        
        # Sort by creation time and return the most recent
        active_sessions.sort(key=lambda x: x['created_at'], reverse=True)
        most_recent = active_sessions[0]
        
        logger.info(f"Retrieved active session: {most_recent['session_id']} (type: {most_recent['session_type']})")
        return most_recent
        
    except Exception as e:
        logger.error(f"Error retrieving active sessions: {str(e)}")
        raise

def process_weight_from_device(data):
    """Process weight data for unified weighing sessions"""
    try:
        device_id = data.get('device_id')
        weight = float(data.get('weight'))
        session_id = data.get('session_id')  # This could be batch_id or rompes_id
        
        if not session_id:
            logger.warning(f"IoT device {device_id} sent weight without session_id")
            return {
                "status": "received",
                "message": "Weight received, no session assigned"
            }
        
        # Determine collection and session type from prefix
        if session_id.startswith('prod_'):
            collection_name = BATCH_COLLECTION
            session_type = 'product'
        elif session_id.startswith('rompes_'):
            collection_name = 'rompes_batches'
            session_type = 'rompes'
        else:
            # Handle legacy IDs - assume product
            collection_name = BATCH_COLLECTION
            session_type = 'product'
        
        # Validate session exists
        session_ref = firestore_client.collection(collection_name).document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            logger.warning(f"IoT device {device_id} tried to update non-existent session {session_id}")
            return {
                "status": "error",
                "message": "Session not found"
            }
        
        # For product sessions, store individual weights in subcollection
        if session_type == 'product':
            weights_ref = session_ref.collection(WEIGHTS_SUBCOLLECTION)
            weight_doc_ref = weights_ref.document()
            
            weight_entry = {
                "weight": weight,
                "timestamp": datetime.utcnow(),
                "device_id": device_id
            }
            
            weight_doc_ref.set(weight_entry)
        
        # Update session total weight for both types
        session_ref.update({
            "total_weight": firestore.Increment(weight)
        })
        
        logger.info(f"Added weight {weight}g to {session_type} session {session_id} from device {device_id}")
        
        return {
            "status": "success",
            "session_id": session_id,
            "session_type": session_type,
            "message": f"Weight added to {session_type} session"
        }
        
    except Exception as e:
        logger.error(f"Error processing IoT weight data: {str(e)}")
        raise