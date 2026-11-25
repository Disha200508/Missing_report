FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first to keep the container small, then app deps and facenet-pytorch
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    torch torchvision

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir \
    flask flask-cors gunicorn werkzeug numpy pillow requests tqdm \
    pymongo dnspython python-dotenv twilio \
    && pip install --no-cache-dir --no-deps facenet-pytorch==2.6.0

COPY backend ./backend
COPY frontend ./frontend
COPY face_model.pt ./face_model.pt

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --chdir backend --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120 app:app"]
