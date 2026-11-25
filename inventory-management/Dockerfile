
FROM python:3.12-slim

WORKDIR /app

# Install the application's Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application into the image.
COPY . .

# Expose the application's port.
EXPOSE 5000

# Start Flask so the container is accessible from the host.
CMD ["python", "-m", "flask", "--app", "run:app", "run", "--host=0.0.0.0", "--port=5000"]
