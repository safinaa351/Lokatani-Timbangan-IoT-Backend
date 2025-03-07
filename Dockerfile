# Pakai base image Python
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy semua file ke container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH agar Python bisa menemukan module `app`
ENV PYTHONPATH=/app

# Expose port Flask
EXPOSE 8080

# Jalankan Flask app
CMD ["python", "main.py"]