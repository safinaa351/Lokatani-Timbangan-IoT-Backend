from google.cloud import storage, firestore
from google.cloud.storage.blob import Blob
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timedelta
import logging
import requests  # For ML service interaction
import cv2
import numpy as np
from ultralytics import YOLO
import gc
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
model = YOLO('app/services/models/weights/best.pt')

def upload_image(file, filename, bucket_name=None):
    try:
        bucket_name = bucket_name or BUCKET_NAME
        bucket = storage_client.bucket(bucket_name)
        file.seek(0)
        blob = bucket.blob(filename)
        blob.upload_from_string(file.read(), content_type=file.content_type)

        signed_url = blob.generate_signed_url(
            expiration=timedelta(minutes=15),
            method='GET'
        )

        logger.info(f"Image uploaded to {bucket_name} with URL: {signed_url}")
        return signed_url
    except Exception as e:
        logger.error(f"Image upload failed: {str(e)}")
        raise

def delete_image(filename, bucket_name=None):
    try:
        bucket_name = bucket_name or BUCKET_NAME
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.delete()
        logger.info(f"Deleted image {filename} from bucket {bucket_name}")
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
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

        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        batch_doc = batch_ref.get()
        if not batch_doc.exists:
            raise ValueError(f"Batch with ID {batch_id} does not exist.")

        update_payload = {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }
        batch_ref.update(update_payload)
        batch_info = batch_ref.get().to_dict()
        logger.info(f"Batch completed: {batch_id}")
        return {
            "batch_id": batch_id,
            "user_id": batch_info.get("user_id"),
            "status": batch_info.get("status"),
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
    img = None
    image_array = None
    results = None
    filename = image_url.split('/')[-1].split('?')[0]  # Extract filename from URL

    try:
        with requests.get(image_url, stream=True) as resp:
            resp.raise_for_status()
            image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            results = model(img)[0]

            detections = []
            for det in results.boxes.data:
                conf = float(det[4])
                class_id = int(det[5])
                detections.append({
                    'vegetable_type': results.names[class_id],
                    'confidence': round(conf, 2)
                })

            if not detections:
                logger.warning("No object detected")
                delete_image(filename)  # Delete image if no object detected
                return {"status": "error", "message": "No object detected"}

            detections.sort(key=lambda x: x['confidence'], reverse=True)
            best_detection = detections[0]

            if best_detection['vegetable_type'] in ["kale", "bayam merah"] and best_detection['confidence'] >= 0.7:
                best_detection["image_url"] = image_url
                best_detection["timestamp"] = datetime.utcnow().isoformat()

                if batch_id:
                    batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
                    batch_ref.update({
                        "vegetable_type": best_detection['vegetable_type'],
                        "confidence": best_detection['confidence'],
                        "image_url": image_url
                    })

                logger.info(f"Detected: {best_detection['vegetable_type']} with {best_detection['confidence']}")
                return best_detection
            else:
                logger.info(f"Detected vegetable is not kale or bayam merah or confidence is below threshold")
                delete_image(filename)  # Delete image if not kale/bayam merah
                return {"status": "error", "message": "bukan kale atau bayam merah"}

    except Exception as e:
        logger.error(f"Vegetable identification error: {str(e)}")
        # Try to delete image in case of error
        try:
            delete_image(filename)
        except:
            pass
        raise

    finally:
        # Explicitly release memory and clear PyTorch cache
        del img
        del image_array
        del results
        gc.collect()

def process_rompes_weighing(file, filename, weight, user_id, notes=''):
    try:
        image_url = upload_image(file, filename, ROMPES_BUCKET_NAME)
        logger.info(f"Rompes image uploaded with URL: {image_url}")

        rompes_id = str(uuid.uuid4())
        rompes_ref = firestore_client.collection('rompes_batches').document(rompes_id)

        rompes_data = {
            "rompes_id": rompes_id,
            "user_id": user_id,
            "weight": weight,
            "image_url": image_url,
            "notes": notes,
            "created_at": datetime.utcnow(),
            "type": "rompes"
        }

        rompes_ref.set(rompes_data)
        logger.info(f"Rompes data saved with ID: {rompes_id}")

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

def get_user_batch_history(user_id):
    """Get batch history for a specific user"""
    try:
        logger.info(f"Retrieving batch history for user: {user_id}")
        batch_ref = firestore_client.collection(BATCH_COLLECTION)
        query = batch_ref.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        batches = []
        for doc in query.stream():
            batch_data = doc.to_dict()
            batch_data['batch_id'] = doc.id
            
            # Format timestamp for display
            if 'created_at' in batch_data and batch_data['created_at']:
                created_at = batch_data['created_at']
                batch_data['formatted_date'] = created_at.strftime('%A, %d-%m-%Y')
                
            # Include only needed fields for the list view
            batches.append({
                'batch_id': doc.id,
                'vegetable_type': batch_data.get('vegetable_type', 'Unknown'),
                'total_weight': batch_data.get('total_weight', 0),
                'image_url': batch_data.get('image_url', ''),
                'formatted_date': batch_data.get('formatted_date', ''),
                'status': batch_data.get('status', '')
            })
            
        logger.info(f"Found {len(batches)} batches for user {user_id}")
        return batches
        
    except Exception as e:
        logger.error(f"Error retrieving batch history: {str(e)}")
        raise

def get_batch_detail(batch_id):
    """Get detailed information about a specific batch"""
    try:
        logger.info(f"Retrieving details for batch: {batch_id}")
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        batch_doc = batch_ref.get()
        
        if not batch_doc.exists:
            logger.warning(f"Batch {batch_id} not found")
            return {
                "status": "error",
                "message": "Batch not found"
            }
            
        batch_data = batch_doc.to_dict()
        batch_data['batch_id'] = batch_id
        
        # Format timestamps
        for time_field in ['created_at', 'completed_at']:
            if time_field in batch_data and batch_data[time_field]:
                batch_data[f'formatted_{time_field}'] = batch_data[time_field].strftime('%A, %d-%m-%Y %H:%M:%S')
        
        # Get individual weights in this batch
        weights = []
        weights_ref = batch_ref.collection(WEIGHTS_SUBCOLLECTION)
        for weight_doc in weights_ref.order_by('timestamp').stream():
            weight_data = weight_doc.to_dict()
            if 'timestamp' in weight_data:
                weight_data['formatted_time'] = weight_data['timestamp'].strftime('%H:%M:%S')
            weights.append(weight_data)
            
        batch_data['weights'] = weights
        logger.info(f"Retrieved batch {batch_id} with {len(weights)} weight entries")
        
        return {
            "status": "success",
            "batch": batch_data
        }
        
    except Exception as e:
        logger.error(f"Error retrieving batch details: {str(e)}")
        raise