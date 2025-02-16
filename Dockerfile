# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final lightweight image
FROM python:3.12-slim
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy the application code
COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Start FastAPI with Uvicorn on port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]



