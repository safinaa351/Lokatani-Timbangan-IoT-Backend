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

def process_weight_from_device(data):
    """Process weight data coming from IoT device"""
    try:
        device_id = data.get('device_id')
        weight = float(data.get('weight'))
        batch_id = data.get('batch_id')
        
        # Validate batch exists if provided
        if batch_id:
            batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                logger.warning(f"IoT device {device_id} tried to update non-existent batch {batch_id}")
                return {
                    "status": "error",
                    "message": "Batch not found"
                }
                
            # Add weight to the weights subcollection
            weights_ref = batch_ref.collection(WEIGHTS_SUBCOLLECTION)
            weight_entry = {
                "weight": weight,
                "timestamp": datetime.utcnow(),
                "device_id": device_id
            }
            weight_doc_ref, _ = weights_ref.add(weight_entry)
            weight_id = weight_doc_ref.id

            
            # Update batch total weight
            batch_ref.update({
                "total_weight": firestore.Increment(weight)
            })
            
            logger.info(f"Added weight {weight}g to batch {batch_id} from device {device_id}")
            
            return {
                "status": "success",
                "batch_id": batch_id,
                "weight_id": weight_id,  # Return the ID of the weight document
                "message": "Weight added to batch"
            }
        else:
            # No batch ID provided - just log the device activity
            logger.info(f"Received weight {weight}g from device {device_id} without batch assignment")
            return {
                "status": "received",
                "message": "Weight received, no batch assigned"
            }
        
    except Exception as e:
        logger.error(f"Error processing IoT weight data: {str(e)}")
        raise

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