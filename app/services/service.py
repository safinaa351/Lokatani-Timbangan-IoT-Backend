from google.cloud import storage, firestore
from google.cloud.storage.blob import Blob
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timedelta
import logging
import requests  # For ML service interaction

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cloud Configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
ROMPES_BUCKET_NAME = os.getenv("ROMPES_BUCKET_NAME")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL")

rompes_storage_client = storage.Client()
storage_client = storage.Client()
firestore_client = firestore.Client()

# Firestore Collection
BATCH_COLLECTION = "vegetable_batches"
WEIGHTS_SUBCOLLECTION = "weights"

def upload_image(file, filename, bucket_name=None):
    """Upload image to GCS and return signed URL
    
    Args:
        file: File object to upload
        filename: Safe filename to use in storage
        bucket_name: Optional bucket override (defaults to standard image bucket)
    """
    try:
        # Use provided bucket or default to standard image bucket
        bucket_name = bucket_name or BUCKET_NAME
        bucket = storage_client.bucket(bucket_name)
        
        # Reset file pointer and upload
        file.seek(0)
        blob = bucket.blob(filename)
        blob.upload_from_string(file.read(), content_type=file.content_type)

        # Generate signed URL
        signed_url = blob.generate_signed_url(
            expiration=timedelta(minutes=15),
            method='GET'
        )

        logger.info(f"Image uploaded to {bucket_name} with URL: {signed_url}")
        return signed_url
    except Exception as e:
        logger.error(f"Image upload failed: {str(e)}")
        raise

def detect_weight(current_weight):
    try:
        # We've already validated in the route handler, so we can trust the weight value
        logger.info(f"Weight detected: {current_weight} grams")
        return {
            "status": "detected",
            "weight": current_weight,
            "notification_required": True
        }
    except Exception as e:
        logger.error(f"Weight detection error: {str(e)}")
        raise

def stabilize_weight(weight_data):
    try:
        batch_id = weight_data.get('batch_id')
        stabilized_weight = weight_data.get('stabilized_weight')
        
        # Reference to batch document
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        weights_ref = batch_ref.collection(WEIGHTS_SUBCOLLECTION)
        
        # Create weight entry
        weight_entry = {
            "weight": stabilized_weight,
            "timestamp": datetime.utcnow(),
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
    try:
        batch_id = str(uuid.uuid4())
        user_id = batch_data.get('user_id')

        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        batch_ref.set({
            "user_id": user_id,
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
    try:
        batch_id = batch_data.get('batch_id')
        if not batch_id:
            raise ValueError("batch_id is required.")
        
        # Reference to batch document
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        batch_doc = batch_ref.get()
        if not batch_doc.exists:
            raise ValueError(f"Batch with ID {batch_id} does not exist.")
        
        # Prepare update payload
        update_payload = {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }
        
        # Update batch document
        batch_ref.update(update_payload)
        
        # Get updated batch info (just one Firestore read)
        batch_info = batch_ref.get().to_dict()
        
        logger.info(f"Batch completed: {batch_id}")
        return {
            "batch_id": batch_id,
            "user_id": batch_info.get("user_id"),
            "status": batch_info.get("status"),  # Should be "completed" now
            "created_at": batch_info.get("created_at"),
            "completed_at": batch_info.get("completed_at"),
            "vegetable_type": batch_info.get("vegetable_type"),
            "total_weight": batch_info.get("total_weight"),
            "confidence": batch_info.get("confidence"),
            "image_url": batch_info.get("image_url")
        }
    except Exception as e:
        logger.error(f"Batch completion error: {str(e)}")
        raise

def identify_vegetable(image_url, batch_id=None):
    try:
        # Mock response (TODO: Replace with actual ML service integration)
        result = {
            "vegetable_type": "bayam merah riil",
            "confidence": 0.90,
            "image_url": image_url,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Uncomment when ML service is ready
        # if ML_SERVICE_URL:
        #     response = requests.post(ML_SERVICE_URL, json={
        #         "image_url": image_url,
        #         "batch_id": batch_id
        #     })
        #     
        #     if response.status_code != 200:
        #         logger.warning(f"ML service error: {response.text}")
        #         return {"status": "error", "message": "Identification failed"}
        #     
        #     result = response.json()
        
        # Save identification to Firestore if batch_id provided
        if batch_id:
            batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
            batch_ref.update({
                "vegetable_type": result.get('vegetable_type'),
                "confidence": result.get('confidence', 0),
                "image_url": result.get('image_url')
            })
        
        logger.info(f"Vegetable identified: {result.get('vegetable_type')}")
        return result
    except Exception as e:
        logger.error(f"Vegetable identification error: {str(e)}")
        raise


#ROMPESSSSSSSSSSSSSSSS
def process_rompes_weighing(file, filename, weight, user_id, notes=''):
    try:
        # Reuse upload_image function
        image_url = upload_image(file, filename, ROMPES_BUCKET_NAME)
        logger.info(f"Rompes image uploaded with URL: {image_url}")
        
        # Create a rompes document in Firestore
        logger.info(f"Creating rompes document in Firestore. Weight: {weight}g")
        rompes_id = str(uuid.uuid4())
        rompes_ref = firestore_client.collection('rompes_batches').document(rompes_id)
        
        # Create document data
        rompes_data = {
            "rompes_id": rompes_id,
            "user_id": user_id,
            "weight": weight,
            "image_url": image_url,
            "notes": notes,
            "created_at": datetime.utcnow(),
            "type": "rompes"  # Explicitly mark as rompes
        }
        
        # Save to Firestore
        rompes_ref.set(rompes_data)
        logger.info(f"Rompes data saved with ID: {rompes_id}")
        
        # Return success result
        return {
            "status": "success",
            "rompes_id": rompes_id,
            "weight": weight,
            "image_url": image_url,
            "message": "Rompes weighing process completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in rompes weighing process: {str(e)}")
        raise
