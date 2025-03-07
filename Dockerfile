# Pakai base image Python
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy semua file ke container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port Flask (sesuai dengan yang ada di `main.py`)
EXPOSE 8080

# Jalankan Flask app
CMD ["python", "app/main.py"]
