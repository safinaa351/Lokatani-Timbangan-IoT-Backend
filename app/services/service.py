from google.cloud import storage, firestore
import os
import uuid
from datetime import datetime
import logging
import requests  # For ML service interaction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cloud Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(BASE_DIR, "cloud-storage-key.json")

BUCKET_NAME = "img-sayur-lokatani"
storage_client = storage.Client()
firestore_client = firestore.Client()

# Collection Names
BATCH_COLLECTION = "vegetable_batches"
WEIGHTS_SUBCOLLECTION = "weights"

# ML Service Configuration (placeholder - replace with actual endpoint)
ML_SERVICE_URL = "https://your-ml-service-endpoint.com/identify"

def upload_image(file, filename):
    """
    Upload file to Google Cloud Storage and return URL.
    
    Args:
        file: File object to upload
        filename: Name of the file
    
    Returns:
        str: Public URL of uploaded image
    """
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(file.read(), content_type=file.content_type)
        
        image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        logger.info(f"Image uploaded successfully: {image_url}")
        return image_url
    except Exception as e:
        logger.error(f"Image upload failed: {str(e)}")
        raise

def detect_weight(weight_data):
    """
    Process initial weight detection from IoT scale.
    
    Args:
        weight_data (dict): Weight detection payload
    
    Returns:
        dict: Processed weight detection result
    """
    try:
        # Basic validation
        if weight_data.get('current_weight', 0) <= 0:
            logger.warning("Invalid weight detected")
            return {"status": "error", "message": "Invalid weight"}
        
        logger.info(f"Weight detected: {weight_data['current_weight']} grams")
        return {
            "status": "detected",
            "weight": weight_data['current_weight'],
            "notification_required": True
        }
    except Exception as e:
        logger.error(f"Weight detection error: {str(e)}")
        raise

def stabilize_weight(weight_data):
    try:
        batch_id = weight_data.get('batch_id')
        stabilized_weight = weight_data.get('stabilized_weight')
        scale_id = weight_data.get('scale_id')
        
        # Reference to batch document
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        weights_ref = batch_ref.collection(WEIGHTS_SUBCOLLECTION)
        
        # Create weight entry
        weight_entry = {
            "weight": stabilized_weight,
            "timestamp": datetime.utcnow(),
            "scale_id": scale_id
        }
        
        # Add to weights subcollection
        weights_ref.add(weight_entry)
        
        # Update total weight in the batch document
        batch_ref.update({
            "total_weight": firestore.Increment(stabilized_weight)
        })
        
        return {
            "status": "stabilized",
            "batch_id": batch_id,
            "weight": stabilized_weight
        }
    except Exception as e:
        logger.error(f"Weight stabilization error: {str(e)}")
        raise

def initiate_batch(batch_data):
    """
    Initiate a new batch tracking session.
    
    Args:
        batch_data (dict): Batch initiation payload
    
    Returns:
        dict: Batch initiation details
    """
    try:
        # Generate unique batch ID
        batch_id = str(uuid.uuid4())
        
        # Create batch document
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        batch_ref.set({
            "user_id": batch_data.get('user_id'),
            "scale_id": batch_data.get('scale_id'),
            "status": "in_progress",
            "created_at": datetime.utcnow(),
            "total_weight": 0
        })
        
        logger.info(f"Batch initiated: {batch_id}")
        return {
            "status": "initiated",
            "batch_id": batch_id,
            "message": "Batch tracking started"
        }
    except Exception as e:
        logger.error(f"Batch initiation error: {str(e)}")
        raise

def complete_batch(batch_data):
    """
    Complete and finalize a batch tracking session
    
    Args:
        batch_data (dict): Batch completion payload
    
    Returns:
        dict: Batch completion result
    """
    try:
        batch_id = batch_data.get('batch_id')
        vegetable_type = batch_data.get('vegetable_type')
        
        # Reference to batch document
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        
        # Prepare update payload
        update_payload = {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }
        
        # Only add vegetable_type if provided
        if vegetable_type:
            update_payload["vegetable_type"] = vegetable_type
        
        # Update batch document
        batch_ref.update(update_payload)
        
        logger.info(f"Batch completed: {batch_id}")
        return {
            "status": "completed",
            "batch_id": batch_id,
            "message": "Batch tracking finished",
            "vegetable_type": vegetable_type
        }
    except Exception as e:
        logger.error(f"Batch completion error: {str(e)}")
        raise

def identify_vegetable(image_url, batch_id=None):
    """
    Process vegetable identification via ML service.
    
    Args:
        image_url (str): URL of uploaded image
        batch_id (str, optional): Associated batch ID
    
    Returns:
        dict: Vegetable identification result
    """
    try:
        # Call ML service (replace with actual ML service integration)
        response = requests.post(ML_SERVICE_URL, json={
            "image_url": image_url,
            "batch_id": batch_id
        })
        
        if response.status_code != 200:
            logger.warning(f"ML service error: {response.text}")
            return {"status": "error", "message": "Identification failed"}
        
        result = response.json()
        
        # Save identification to Firestore if batch_id provided
        if batch_id:
            batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
            batch_ref.update({
                "vegetable_type": result.get('vegetable_type'),
                "confidence": result.get('confidence', 0)
            })
        
        logger.info(f"Vegetable identified: {result.get('vegetable_type')}")
        return result
    except Exception as e:
        logger.error(f"Vegetable identification error: {str(e)}")
        raise

# Legacy functions (kept for backwards compatibility)
def save_weight(sayur_name, weight, image_url):
    """
    Deprecated: Use batch tracking methods instead
    """
    logger.warning("Using deprecated save_weight method")
    batch_id = initiate_batch({"user_id": "legacy_user"})['batch_id']
    stabilize_weight({
        "batch_id": batch_id,
        "stabilized_weight": weight
    })
    complete_batch({
        "batch_id": batch_id,
        "total_weight": weight,
        "vegetable_type": sayur_name
    })
    return {
        "message": "Legacy weight saving completed",
        "batch_id": batch_id,
        "name": sayur_name,
        "weight": weight
    }