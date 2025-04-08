# Pakai base image Python
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy semua file ke container
COPY . .

# Instal dependensi sistem yang diperlukan (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH agar Python bisa menemukan module `app`
ENV PYTHONPATH=/app

# Expose port Flask
EXPOSE 8080

# Jalankan Flask app
CMD ["python", "main.py"]