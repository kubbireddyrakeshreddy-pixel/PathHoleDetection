"""
detector.py — YOLOv11 pothole segmentation engine.

Loads the trained model once at startup and exposes a single `detect()`
function that takes an image path and returns:
  - annotated image bytes (PNG)
  - list of detection dicts  { x1,y1,x2,y2, conf, cls_name, area_pixels }
  - max confidence score
  - boolean pothole_detected
  - count of detections
  - damage_percentage (float)
"""
import os
import io
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

# Global model instance (loaded once)
_model = None


def load_model(model_path: str = "best.pt"):
    """Load YOLOv11 weights into memory."""
    global _model
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model weights not found at '{model_path}'. "
            "Please run the Colab segmentation notebook and place best.pt in the backend/ folder."
        )
    _model = YOLO(model_path)
    print(f"[Detector] Segmentation Model loaded from '{model_path}'")


def detect(image_path: str, confidence_threshold: float = 0.40):
    """
    Run YOLOv11 segmentation inference on an image.
    """
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    # ------------------------------------------------------------------ read
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Cannot read image at path: {image_path}")

    total_pixels = img_bgr.shape[0] * img_bgr.shape[1]

    # ----------------------------------------------------------------- infer
    results = _model.predict(
        source=img_bgr,
        conf=confidence_threshold,
        iou=0.45,
        imgsz=640,
        verbose=False,
    )

    result = results[0]
    detections = []
    max_conf = 0.0
    total_damage_area = 0.0

    masks_xy = []
    if result.masks is not None:
        masks_xy = result.masks.xy

    for i, box in enumerate(result.boxes):
        conf = float(box.conf[0])
        cls  = int(box.cls[0])
        name = result.names[cls]
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        
        area = 0
        if i < len(masks_xy):
            polygon = masks_xy[i].astype(np.int32)
            if len(polygon) >= 3:
                area = cv2.contourArea(polygon)
                total_damage_area += area

        detections.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "confidence": round(conf, 4),
            "class_name": name,
            "area_pixels": area
        })
        max_conf = max(max_conf, conf)

    damage_percentage = (total_damage_area / total_pixels) * 100 if total_pixels > 0 else 0.0

    # ------------------------------------------------- draw annotated image
    annotated_bgr = _draw_masks_and_boxes(img_bgr.copy(), masks_xy, detections)
    annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
    pil_img       = Image.fromarray(annotated_rgb)
    buf           = io.BytesIO()
    pil_img.save(buf, format="PNG")
    annotated_bytes = buf.getvalue()

    return {
        "annotated_bytes":   annotated_bytes,
        "detections":        detections,
        "max_confidence":    round(max_conf, 4),
        "pothole_detected":  len(detections) > 0,
        "num_potholes":      len(detections),
        "damage_percentage": round(damage_percentage, 2)
    }


def _draw_masks_and_boxes(img_bgr: np.ndarray, masks_xy: list, detections: list) -> np.ndarray:
    """Draw beautiful transparent green masks and thin bounding boxes."""
    overlay = img_bgr.copy()
    
    # Draw green masks
    for mask in masks_xy:
        polygon = mask.astype(np.int32)
        if len(polygon) >= 3:
            cv2.fillPoly(overlay, [polygon], (0, 255, 0)) # Green

    # Blend masks with original image (alpha 0.45 makes it semi-transparent)
    alpha = 0.45
    img_bgr = cv2.addWeighted(overlay, alpha, img_bgr, 1 - alpha, 0)

    # Draw boxes & labels
    for det in detections:
        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
        conf  = det["confidence"]
        
        # We don't show the pixel area on the box to keep it clean, just the class and conf
        label = f"{det['class_name']} {conf:.0%}"
        color = (0, 0, 220) # Red
        
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(img_bgr, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
        cv2.putText(img_bgr, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    return img_bgr
