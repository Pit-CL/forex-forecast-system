FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy Python files and directories explicitly
COPY __init__.py .
COPY main.py .

# Create directories first
RUN mkdir -p /app/models /app/routers /app/services /app/utils /app/auth /app/mock_data
RUN mkdir -p /app/data /app/output /app/data/warehouse

# Copy Python files individually
COPY models/__init__.py ./models/__init__.py
COPY models/schemas.py ./models/schemas.py
COPY routers/ ./routers/
COPY services/ ./services/
COPY utils/ ./utils/
COPY auth/ ./auth/
COPY mock_data/ ./mock_data/

ENV DEVELOPMENT_MODE=false
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3     CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
