from flask import Blueprint, request, jsonify
import imghdr
from app.services.service import upload_image, save_weight, create_batch, generate_upload_url
from app.auth import iot_api_key_required

routes = Blueprint('routes', __name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    """Cek apakah file memiliki ekstensi gambar yang valid"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@routes.route('/')
def home():
    return "Tes modifikasi"

@routes.route('/upload_with_weight', methods=['POST'])
def upload_with_weight():
    """API untuk upload gambar & simpan berat sayur ke Firestore."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Cek ekstensi file
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only PNG, JPG, and JPEG are allowed."}), 400

    # Cek MIME type agar hanya file gambar yang bisa di-upload
    file_type = imghdr.what(file)
    if file_type not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Invalid file content. Only images are allowed."}), 400

    sayur_name = request.form.get("name")
    weight = request.form.get("weight")

    if not sayur_name or not weight:
        return jsonify({"error": "Missing 'name' or 'weight'"}), 400

    try:
        image_url = upload_image(file, file.filename)  # Upload gambar
        result = save_weight(sayur_name, int(weight), image_url)  # Simpan data ke Firestore
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== NEW ROUTES (Add below existing routes) ==========
@routes.route('/api/weight', methods=['POST'])
@iot_api_key_required
def handle_weight_update():
    """Endpoint for IoT devices to send weight updates."""
    data = request.get_json()
    new_weight = data.get("weight")
    
    # TODO: Add your stabilization logic here
    return jsonify({"status": "received", "weight": new_weight})

@routes.route('/api/generate-upload-url', methods=['GET'])
def handle_generate_upload_url():
    """Generate signed URL for mobile app to upload photos directly."""
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"error": "filename parameter required"}), 400
    
    url = generate_upload_url(filename)
    return jsonify({"url": url})

@routes.route('/api/batches', methods=['POST'])
def handle_create_batch():
    """Create a new batch with cached weights and photo."""
    data = request.get_json()
    
    # Validate weights are numbers
    try:
        weights = [float(w) for w in data.get("weights")]
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid weights format"}), 400
    
    # Validate photo_url is a string
    if not isinstance(data.get("photo_url"), str):
        return jsonify({"error": "Invalid photo_url"}), 400
    
    # Proceed to create batch
    batch_id = create_batch({"weights": weights, "photo_url": data["photo_url"]})
    return jsonify({"batch_id": batch_id}), 201