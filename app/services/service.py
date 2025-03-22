from google.cloud import storage, firestore
import os
from datetime import datetime
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(BASE_DIR, "cloud-storage-key.json")

BUCKET_NAME = "img-sayur-lokatani"
storage_client = storage.Client()

# Setup Firestore
firestore_client = firestore.Client()
COLLECTION_NAME = "berat-sayuran"
# New Firestore collection for batches
BATCH_COLLECTION = "batches"

def create_batch(batch_data: dict):
    """Create a new batch with weights subcollection (new structure)."""
    batch_ref = firestore_client.collection(BATCH_COLLECTION).document()
    
    # Main batch data
    batch_ref.set({
        "timestamp": datetime.utcnow(),
        "total_weight": sum(batch_data["weights"]),
        "status": "pending",
        "photo_url": batch_data.get("photo_url", "")
    })
    
    # Add weights as subcollection
    weights_collection = batch_ref.collection("weights")
    for idx, weight in enumerate(batch_data["weights"]):
        weights_collection.add({
            "order": idx + 1,
            "value": weight,
            "timestamp": datetime.utcnow()
        })
    
    return batch_ref.id

def generate_upload_url(filename: str):
    """Generate signed URL for direct upload to Cloud Storage (replaces upload_image)."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"batch_photos/{filename}")
    return blob.generate_signed_url(
        version="v4",
        expiration=3600,  # 1 hour
        method="PUT",
        content_type="image/jpeg"
    )

def upload_image(file, filename):
    """Upload file ke Google Cloud Storage dan return URL-nya."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(file.read(), content_type=file.content_type)
    
    image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return image_url

def save_weight(sayur_name, weight, image_url):
    """Simpan berat sayur ke Firestore."""
    sayur_id = str(uuid.uuid4())  # Generate ID unik
    doc_ref = firestore_client.collection(COLLECTION_NAME).document(sayur_id)
    doc_ref.set({
        "id": sayur_id,
        "name": sayur_name,
        "weight": weight,
        "image_url": image_url,
        "timestamp": datetime.utcnow()  # Simpan waktu UTC
    })

    return {
        "message": "Data berhasil disimpan",
        "id": sayur_id,
        "name": sayur_name,
        "weight": weight,
        "image_url": image_url,
        "timestamp": datetime.utcnow().isoformat()  # Format timestamp biar rapi
    }