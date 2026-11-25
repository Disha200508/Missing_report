import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from deepface import DeepFace

app = FastAPI(title="Face Verification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = "ArcFace"          # pretrained; swap later for your own model
DETECTOR = "opencv"        # use "retinaface" or "mtcnn" for better accuracy


def read_image(upload: UploadFile) -> np.ndarray:
    data = np.frombuffer(upload.file.read(), np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, f"{upload.filename} is not a valid image")
    return img


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/verify")
def verify(image1: UploadFile = File(...), image2: UploadFile = File(...)):
    img1, img2 = read_image(image1), read_image(image2)
    try:
        r = DeepFace.verify(
            img1_path=img1,
            img2_path=img2,
            model_name=MODEL,
            detector_backend=DETECTOR,
            distance_metric="cosine",
            enforce_detection=True,
        )
    except ValueError:
        raise HTTPException(422, "No face detected in one of the images. Use a clear, front-facing photo.")

    distance = float(r["distance"])
    threshold = float(r["threshold"])
    return {
        "verified": bool(r["verified"]),
        "distance": round(distance, 4),
        "threshold": round(threshold, 4),
        "similarity": round(max(0.0, 1 - distance) * 100, 1),
    }