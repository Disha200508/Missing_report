"""Face recognition engine: MTCNN (detect+align) -> trained ResNet18/FaceNet embedder -> cosine distance."""
import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
from torchvision.models import resnet18
from facenet_pytorch import InceptionResnetV1, MTCNN

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_CANDIDATES = [
    os.path.join(HERE, "face_model.pt"),
    os.path.join(HERE, "..", "face_model.pt"),
]
DEFAULT_FACENET_THRESHOLD = 0.38
DEFAULT_CUSTOM_THRESHOLD = 0.055

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class NoFaceError(Exception):
    pass


class FaceEmbedder(nn.Module):
    """ResNet-18 backbone + linear/BatchNorm projection head producing L2-normalized embeddings."""

    def __init__(self, emb_dim: int = 512):
        super().__init__()
        self.backbone = resnet18(weights=None)
        self.backbone.fc = nn.Identity()
        self.head = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(512, emb_dim),
            nn.BatchNorm1d(emb_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.head(self.backbone(x)), dim=1)


def _resolve_model_path() -> str | None:
    for path in MODEL_CANDIDATES:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None


def _extract_state_and_threshold(ckpt):
    if isinstance(ckpt, dict) and any(k in ckpt for k in ("model", "state_dict", "model_state_dict")):
        state = ckpt.get("model") or ckpt.get("state_dict") or ckpt.get("model_state_dict")
        threshold = ckpt.get("threshold")
        return state, float(threshold) if threshold is not None else None
    return ckpt, None


class FaceEngine:
    def __init__(self):
        try:
            torch.set_num_threads(1)
        except Exception:
            pass
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._is_resnet_embedder = False
        self._norm = transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD)

        # Allow switching backbone via environment variable (default: 'facenet' for reliable face discrimination)
        backbone_choice = os.environ.get("FACE_BACKBONE", "facenet").strip().lower()
        custom_threshold_env = os.environ.get("FACE_THRESHOLD")

        if backbone_choice == "custom":
            model_path = _resolve_model_path()
            if model_path:
                try:
                    ckpt = torch.load(model_path, map_location=self.device, weights_only=True)
                except Exception:
                    ckpt = torch.load(model_path, map_location=self.device, weights_only=False)

                state, ckpt_threshold = _extract_state_and_threshold(ckpt)
                if custom_threshold_env is not None:
                    self.threshold = float(custom_threshold_env)
                elif ckpt_threshold is not None:
                    self.threshold = ckpt_threshold
                else:
                    self.threshold = DEFAULT_CUSTOM_THRESHOLD

                if isinstance(state, dict) and any(k.startswith("backbone.") for k in state):
                    emb_dim = int(state["head.1.weight"].shape[0]) if "head.1.weight" in state else 512
                    self.model = FaceEmbedder(emb_dim=emb_dim).to(self.device)
                    self.model.load_state_dict(state, strict=True)
                    self._is_resnet_embedder = True
                    self.mtcnn = MTCNN(image_size=160, margin=20, post_process=False, device=self.device)
                    print(f"[face] loaded custom ResNet18 model from {model_path}, threshold={self.threshold:.3f}")
                else:
                    self.model = InceptionResnetV1(pretrained="vggface2").to(self.device)
                    self.model.load_state_dict(state)
                    self.mtcnn = MTCNN(image_size=160, margin=20, device=self.device)
                    print(f"[face] loaded custom FaceNet model from {model_path}, threshold={self.threshold:.3f}")
            else:
                self.threshold = float(custom_threshold_env) if custom_threshold_env else DEFAULT_FACENET_THRESHOLD
                self.model = InceptionResnetV1(pretrained="vggface2").to(self.device)
                self.mtcnn = MTCNN(image_size=160, margin=20, device=self.device)
                print(f"[face] custom model not found, falling back to FaceNet (VGGFace2), threshold={self.threshold:.3f}")
        else:
            # Default production backbone: FaceNet (VGGFace2) with verified face/gender separation
            self.threshold = float(custom_threshold_env) if custom_threshold_env else DEFAULT_FACENET_THRESHOLD
            self.model = InceptionResnetV1(pretrained="vggface2").to(self.device)
            self.mtcnn = MTCNN(image_size=160, margin=20, device=self.device)
            print(f"[face] loaded pre-trained FaceNet (VGGFace2), threshold={self.threshold:.3f}")

        self.model.eval()

    def embed(self, image_path: str) -> np.ndarray:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
        face = self.mtcnn(rgb_img)
        if face is None:
            raise NoFaceError("No face detected in the photo")
        if self._is_resnet_embedder:
            face = self._norm(face / 255.0)
        else:
            if face.max() > 1.0:
                face = (face - 127.5) / 128.0
        with torch.no_grad():
            e = self.model(face.unsqueeze(0).to(self.device))
            e = F.normalize(e, dim=1)
        del face
        return e[0].cpu().numpy().astype("float32")

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(1.0 - np.dot(a, b))

    def score(self, dist: float) -> int:
        """Convert distance to a 0-100 'match confidence' for display."""
        return int(round(max(0.0, min(1.0, 1 - dist / (2 * self.threshold))) * 100))
