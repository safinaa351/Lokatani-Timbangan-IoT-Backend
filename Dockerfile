FROM python:3.10-slim

# Install system dependencies for OpenCV, YOLO, and Pillow
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    git \
    # Dependencies for Pillow
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Pillow explicitly before other requirements
RUN pip install --no-cache-dir Pillow==10.1.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "main:app", "--max-requests", "100", "--max-requests-jitter", "10"]