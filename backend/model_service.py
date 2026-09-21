"""
AI inference service for jackfruit tree and fruit disease classification.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import torch
from dotenv import load_dotenv
from PIL import Image
from torchvision import models, transforms

os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).parent.parent / ".ultralytics"))
from ultralytics import YOLO

load_dotenv()

CLASS_NAMES = os.getenv(
    "CLASS_NAMES",
    "pink_disease,stem_cracking_gummosis,batocera_rufomaculata,stripe_canker"
).split(",")

JACKFRUIT_CLASS_NAMES = os.getenv(
    "JACKFRUIT_CLASS_NAMES",
    "healthy,fruit_borer,fruit_rot,anthracnose"
).split(",")

BASE_DIR = Path(__file__).parent.parent


class ModelService:
    """Load and run YOLO classification models plus EfficientNet-B0 checkpoints."""

    def __init__(self):
        self.models: Dict[str, object] = {}
        self.model_types: Dict[str, str] = {}
        self.class_names: Dict[str, List[str]] = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.efficientnet_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self._load_models()

    def _load_models(self):
        yolo_model_paths = {
            "best_11": os.getenv("MODEL_PATH_11", str(BASE_DIR / "models" / "best_11.pt")),
            "best_26": os.getenv("MODEL_PATH_26", str(BASE_DIR / "models" / "best_26.pt")),
            "jackfruit_yolov26m_cls": os.getenv("JACKFRUIT_YOLO_MODEL_PATH", str(BASE_DIR / "models" / "best.pt")),
        }

        for name, path in yolo_model_paths.items():
            if Path(path).exists():
                print(f"[ModelService] Loading YOLO model: {name} from {path}")
                self.models[name] = YOLO(path)
                self.model_types[name] = "yolo_cls"
                print(f"[ModelService] OK: {name} loaded")
            else:
                print(f"[ModelService] Model not found: {path}")

        efficientnet_path = os.getenv(
            "JACKFRUIT_EFFICIENTNET_MODEL_PATH",
            str(BASE_DIR / "models" / "best_jackfruit_model.pth"),
        )
        if Path(efficientnet_path).exists():
            try:
                print(f"[ModelService] Loading EfficientNet-B0 model from {efficientnet_path}")
                self._load_efficientnet("jackfruit_efficientnet_b0", efficientnet_path)
                print("[ModelService] OK: jackfruit_efficientnet_b0 loaded")
            except Exception as exc:
                print(f"[ModelService] Cannot load EfficientNet-B0 model {efficientnet_path}: {exc}")
        else:
            print(f"[ModelService] Model not found: {efficientnet_path}")

    def _load_efficientnet(self, name: str, path: str):
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        state_dict = checkpoint
        class_names: Optional[List[str]] = None

        if isinstance(checkpoint, dict):
            for key in ("class_names", "classes", "idx_to_class"):
                if key in checkpoint:
                    value = checkpoint[key]
                    class_names = [value[i] for i in sorted(value)] if isinstance(value, dict) else list(value)
                    break

            for key in ("model_state_dict", "state_dict", "model"):
                if key in checkpoint and isinstance(checkpoint[key], dict):
                    state_dict = checkpoint[key]
                    break

        if not isinstance(state_dict, dict):
            raise ValueError("Checkpoint khong chua state_dict hop le")

        state_dict = {
            key.replace("module.", ""): value
            for key, value in state_dict.items()
            if hasattr(value, "shape")
        }

        classifier_weight = None
        for key in ("classifier.1.weight", "classifier.weight", "_fc.weight"):
            if key in state_dict:
                classifier_weight = state_dict[key]
                break

        num_classes = len(class_names or JACKFRUIT_CLASS_NAMES)
        if classifier_weight is not None:
            num_classes = int(classifier_weight.shape[0])

        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_features, num_classes)
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        if missing or unexpected:
            print(f"[ModelService] EfficientNet load note - missing: {missing}, unexpected: {unexpected}")

        model.to(self.device)
        model.eval()
        self.models[name] = model
        self.model_types[name] = "efficientnet_b0"
        self.class_names[name] = self._normalize_class_names(class_names, num_classes)

    def _normalize_class_names(self, class_names: Optional[List[str]], num_classes: int) -> List[str]:
        names = class_names or JACKFRUIT_CLASS_NAMES
        if len(names) < num_classes:
            names = names + [f"class_{idx}" for idx in range(len(names), num_classes)]
        return names[:num_classes]

    def predict(self, image: Image.Image, model_name: str = "best_11") -> dict:
        """
        Run inference on an image.
        Returns: {predicted_class, confidence, all_scores, model_used}
        """
        if model_name not in self.models:
            available = list(self.models.keys())
            if not available:
                raise ValueError("Khong co model nao duoc load!")
            model_name = available[0]

        model_type = self.model_types.get(model_name, "yolo_cls")
        if model_type == "efficientnet_b0":
            return self._predict_efficientnet(image, model_name)

        return self._predict_yolo(image, model_name)

    def _predict_yolo(self, image: Image.Image, model_name: str) -> dict:
        model = self.models[model_name]
        results = model(image, verbose=False)
        result = results[0]

        probs = result.probs
        top1_idx = int(probs.top1)
        top1_conf = float(probs.top1conf)

        names = result.names
        predicted_class = names.get(top1_idx, CLASS_NAMES[top1_idx] if top1_idx < len(CLASS_NAMES) else "unknown")

        all_scores = {}
        for idx, conf in enumerate(probs.data.tolist()):
            class_name = names.get(idx, CLASS_NAMES[idx] if idx < len(CLASS_NAMES) else f"class_{idx}")
            all_scores[class_name] = round(conf, 4)

        return {
            "predicted_class": predicted_class,
            "confidence": round(top1_conf, 4),
            "all_scores": json.dumps(all_scores),
            "model_used": model_name,
        }

    def _predict_efficientnet(self, image: Image.Image, model_name: str) -> dict:
        model = self.models[model_name]
        tensor = self.efficientnet_transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0].detach().cpu()

        top1_idx = int(torch.argmax(probs).item())
        top1_conf = float(probs[top1_idx].item())
        names = self.class_names.get(model_name, self._normalize_class_names(None, len(probs)))
        predicted_class = names[top1_idx] if top1_idx < len(names) else f"class_{top1_idx}"

        all_scores = {
            names[idx] if idx < len(names) else f"class_{idx}": round(float(conf), 4)
            for idx, conf in enumerate(probs.tolist())
        }

        return {
            "predicted_class": predicted_class,
            "confidence": round(top1_conf, 4),
            "all_scores": json.dumps(all_scores),
            "model_used": model_name,
        }

    def get_available_models(self):
        return [
            {
                "name": name,
                "type": self.model_types.get(name, "unknown"),
                "class_names": self.class_names.get(name, []),
            }
            for name in self.models.keys()
        ]


model_service = ModelService()
