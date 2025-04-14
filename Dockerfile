# UNTUK DEMO: docker run -p 8080:8080 --env-file .env vegetable-iot-backend:latest
FROM python:3.10-slim

# Tambahin sistem dependencies untuk OpenCV + YOLO
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
