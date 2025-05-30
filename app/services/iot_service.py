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
            
            # Define weights_ref here
            weights_ref = batch_ref.collection(WEIGHTS_SUBCOLLECTION)

            # Create document reference with auto ID first
            weight_doc_ref = weights_ref.document()  # Creates document with auto ID
            weight_id = weight_doc_ref.id  # Get the ID

            # Create the weight entry with all the data
            weight_entry = {
                "weight": weight,
                "timestamp": datetime.utcnow(),
                "device_id": device_id
            }

            # Set the document data
            weight_doc_ref.set(weight_entry)

            # Update batch total weight
            batch_ref.update({
                "total_weight": firestore.Increment(weight)
            })
            
            logger.info(f"Added weight {weight}g to batch {batch_id} from device {device_id}")
            
            return {
                "status": "success",
                "batch_id": batch_id,
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

def get_active_batch():
    """Get the most recent active batch that hasn't been completed"""
    try:
        batch_ref = firestore_client.collection(BATCH_COLLECTION)
        query = batch_ref.where('status', '==', 'in_progress')\
                        .order_by('created_at', direction=firestore.Query.DESCENDING)\
                        .limit(1)
        
        batches = list(query.stream())
        
        if not batches:
            logger.info("No active batch found")
            return None
            
        batch = batches[0]
        batch_data = batch.to_dict()
        batch_data['batch_id'] = batch.id
        
        logger.info(f"Retrieved active batch: {batch.id}")
        return batch_data
        
    except Exception as e:
        logger.error(f"Error retrieving active batch: {str(e)}")
        raise