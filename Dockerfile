FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Render/Heroku override this with $PORT)
EXPOSE 8080

# Run the FastAPI server
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
