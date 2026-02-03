import fitz
import cv2
import numpy as np
import os
import torch
import uuid
import json
from datetime import datetime
import os

# === PADDLE 3.x WINDOWS STABILITY MODE ===
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# Force legacy executor (disables PIR backend that crashes on Windows)
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_new_executor"] = "0"

from paddleocr import PaddleOCR
from sentence_transformers import SentenceTransformer
from transformers import LayoutLMv3Processor, LayoutLMv3Model


# =========================
# CHECKBOX DETECTOR
# =========================
class CheckboxDetector:
    def detect(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV, 15, 3
        )

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if 10 < w < 40 and 10 < h < 40:
                boxes.append((x, y, w, h))

        return boxes


# =========================
# TABLE EXTRACTOR
# =========================
class TableExtractor:
    def extract(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY, 15, 5
        )

        horiz = cv2.morphologyEx(
            binary, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        )
        vert = cv2.morphologyEx(
            binary, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        )

        grid = cv2.add(horiz, vert)
        contours, _ = cv2.findContours(
            grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        cells = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > 50 and h > 20:
                cells.append((x, y, w, h))

        return sorted(cells, key=lambda x: (x[1], x[0]))


# =========================
# MAIN AI ENGINE
# =========================
class DocumentAIEngine:
    def __init__(self, audit_dir="audit"):
        print("Loading AI models...")

        # OCR (Offline, Stable CPU Mode)
        self.ocr = PaddleOCR(
            lang="en",
            use_angle_cls=True
        )


        # Semantic Matching
        self.matcher = SentenceTransformer("all-MiniLM-L6-v2")

        # Layout Understanding (No classifier head yet — stable mode)
        self.processor = LayoutLMv3Processor.from_pretrained(
            "microsoft/layoutlmv3-base", apply_ocr=False
        )
        self.layout_model = LayoutLMv3Model.from_pretrained(
            "microsoft/layoutlmv3-base"
        )

        # Vision Modules
        self.checkbox_detector = CheckboxDetector()
        self.table_extractor = TableExtractor()

        # Audit System
        self.audit_dir = audit_dir
        os.makedirs(self.audit_dir, exist_ok=True)


    # =========================
    # MAIN PIPELINE
    # =========================
    def fill_pdf(self, pdf_path, excel_data, output_path):
        doc_id = uuid.uuid4().hex
        audit_data = {
            "document_id": doc_id,
            "timestamp": datetime.now().isoformat(),
            "fields": [],
            "approved": False
        }

        doc = fitz.open(pdf_path)

        for page_index in range(len(doc)):
            page = doc[page_index]

            pix = page.get_pixmap(dpi=200)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )

            ocr_tokens = self._run_ocr(img)
            detected_fields = self._detect_visual_fields(img, ocr_tokens)

            matched_fields = self._semantic_match(
                detected_fields, excel_data
            )

            self._write_to_pdf(page, matched_fields)

            audit_data["fields"].extend(matched_fields)

            # Checkbox detection
            checkboxes = self.checkbox_detector.detect(img)
            self._process_checkboxes(page, checkboxes, excel_data)

            # Table detection (stored for review UI, not auto-filled yet)
            tables = self.table_extractor.extract(img)
            audit_data["tables"] = tables

        doc.save(output_path)
        doc.close()

        # Save audit file
        audit_path = os.path.join(self.audit_dir, f"{doc_id}.json")
        with open(audit_path, "w") as f:
            json.dump(audit_data, f, indent=2)

        return output_path, doc_id

    # =========================
    # OCR (VERSION SAFE)
    # =========================
    def _run_ocr(self, image):
        try:
            results = self.ocr.ocr(image)
        except TypeError:
            results = self.ocr.ocr(image, cls=True)

        tokens = []
        if not results or not results[0]:
            return tokens

        for line in results[0]:
            box = line[0]
            text = line[1][0]
            conf = float(line[1][1]) if len(line[1]) > 1 else 0.9

            tokens.append({
                "text": text,
                "box": box,
                "confidence": conf
            })

        return tokens

    # =========================
    # VISUAL FIELD DETECTION
    # =========================
    def _detect_visual_fields(self, image, ocr_tokens):
        fields = []
        for token in ocr_tokens:
            label = token["text"]
            if len(label) > 2:
                fields.append({
                    "label": label,
                    "box": token["box"],
                    "ocr_conf": token["confidence"]
                })
        return fields

    # =========================
    # SEMANTIC MATCHING
    # =========================
    def _semantic_match(self, fields, excel_data):
        results = []

        excel_keys = list(excel_data.keys())
        excel_embeds = self.matcher.encode(excel_keys)

        for field in fields:
            field_embed = self.matcher.encode(field["label"])
            scores = np.dot(excel_embeds, field_embed)

            best_idx = int(np.argmax(scores))
            best_key = excel_keys[best_idx]

            semantic_score = float(scores[best_idx])
            ocr_score = field["ocr_conf"]
            spatial_score = 0.7  # Placeholder for layout proximity model

            confidence = self.compute_confidence(
                semantic_score, ocr_score, spatial_score
            )

            results.append({
                "label": field["label"],
                "box": field["box"],
                "value": excel_data.get(best_key, ""),
                "matched_key": best_key,
                "confidence": confidence,
                "approved": False
            })

        return results

    # =========================
    # CONFIDENCE ENGINE
    # =========================
    def compute_confidence(self, semantic, ocr, spatial):
        return round(
            (0.5 * semantic) +
            (0.3 * ocr) +
            (0.2 * spatial),
            3
        )

    # =========================
    # PDF WRITER
    # =========================
    def _write_to_pdf(self, page, matches):
        for match in matches:
            if match["confidence"] < 0.5:
                continue

            box = match["box"]
            x = box[0][0]
            y = box[0][1]

            page.insert_text(
                (x, y),
                str(match["value"]),
                fontsize=10
            )

    # =========================
    # CHECKBOX HANDLING
    # =========================
    def _process_checkboxes(self, page, boxes, excel_data):
        for key, value in excel_data.items():
            if str(value).lower() in ["yes", "true", "1", "male", "female", "no"]:
                for box in boxes:
                    self._tick_checkbox(page, box)

    def _tick_checkbox(self, page, box):
        x, y, w, h = box
        page.insert_text(
            (x + 3, y + h - 3),
            "✓",
            fontsize=12
        )
