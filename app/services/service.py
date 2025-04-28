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

### commented because the weight will be handled directly from iot device
""" def stabilize_weight(weight_data):
    try:
        batch_id = weight_data.get('batch_id')
        stabilized_weight = weight_data.get('stabilized_weight')
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        weights_ref = batch_ref.collection(WEIGHTS_SUBCOLLECTION)
        weight_entry = {
            "weight": stabilized_weight,
            "timestamp": datetime.utcnow(),
        }
        weights_ref.add(weight_entry)
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
        raise """

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
    try:
        resp = requests.get(image_url, stream=True)
        resp.raise_for_status()
        image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        model = YOLO('yolov8s.pt')
        results = model(img)[0]

        best_detection = None
        highest_conf = 0

        for det in results.boxes.data:
            conf = float(det[4])
            if conf > highest_conf:
                highest_conf = conf
                class_id = int(det[5])
                best_detection = {
                    'vegetable_type': results.names[class_id],
                    'confidence': round(conf, 2)
                }

        if not best_detection:
            logger.warning("No object detected")
            return {"status": "error", "message": "No object detected"}

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

    except Exception as e:
        logger.error(f"Vegetable identification error: {str(e)}")
        raise

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
