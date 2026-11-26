FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    TZ="Asia/Kolkata"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 tzdata \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first to avoid typing-extensions metadata parsing bugs
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install CPU-only PyTorch with --extra-index-url so default PyPI dependencies remain reachable
RUN pip install --no-cache-dir torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --no-deps facenet-pytorch==2.6.0 \
    && python -c "from facenet_pytorch import InceptionResnetV1; InceptionResnetV1(pretrained='vggface2')"

COPY backend ./backend
COPY frontend ./frontend
COPY face_model.pt ./face_model.pt

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --chdir backend --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120 app:app"]
