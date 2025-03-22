from functools import wraps
from flask import request, jsonify
import os

def iot_api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-IOT-API-KEY')
        if api_key != os.getenv("IOT_API_KEY"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated