import fitz
import cv2
import numpy as np
import os
import torch
from paddleocr import PaddleOCR
from sentence_transformers import SentenceTransformer
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification

class DocumentAIEngine:
    def __init__(self):
        print("Loading AI models...")
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
        self.matcher = SentenceTransformer("all-MiniLM-L6-v2")

        self.processor = LayoutLMv3Processor.from_pretrained(
            "microsoft/layoutlmv3-base", apply_ocr=False
        )
        self.layout_model = LayoutLMv3ForTokenClassification.from_pretrained(
            "microsoft/layoutlmv3-base"
        )

    # -------------------------------
    # MAIN PIPELINE
    # -------------------------------
    def fill_pdf(self, pdf_path, excel_data, output_path):
        doc = fitz.open(pdf_path)

        for page_index in range(len(doc)):
            page = doc[page_index]
            pix = page.get_pixmap(dpi=200)

            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )

            ocr_results = self._run_ocr(img)
            layout_fields = self._detect_fields(img, ocr_results)
            matched = self._semantic_match(layout_fields, excel_data)

            self._write_to_pdf(page, matched)

        doc.save(output_path)
        doc.close()
        return output_path

    # -------------------------------
    # OCR
    # -------------------------------
    def _run_ocr(self, image):
        results = self.ocr.ocr(image, cls=True)
        tokens = []

        for line in results[0]:
            box = line[0]
            text = line[1][0]
            tokens.append({"text": text, "box": box})

        return tokens

    # -------------------------------
    # LAYOUT AI
    # -------------------------------
    def _detect_fields(self, image, ocr_tokens):
        words = [t["text"] for t in ocr_tokens]
        boxes = [self._normalize_box(t["box"], image.shape) for t in ocr_tokens]

        encoding = self.processor(
            image,
            words,
            boxes=boxes,
            return_tensors="pt",
            truncation=True,
            padding="max_length"
        )

        with torch.no_grad():
            outputs = self.layout_model(**encoding)

        predictions = outputs.logits.argmax(-1).squeeze().tolist()

        fields = []
        for token, pred in zip(ocr_tokens, predictions):
            if pred > 0:  # non-background
                fields.append({
                    "label": token["text"],
                    "box": token["box"]
                })

        return fields

    # -------------------------------
    # SEMANTIC MATCHING
    # -------------------------------
    def _semantic_match(self, fields, excel_data):
        results = []
        excel_keys = list(excel_data.keys())
        excel_embeds = self.matcher.encode(excel_keys)

        for field in fields:
            field_embed = self.matcher.encode(field["label"])
            scores = np.dot(excel_embeds, field_embed)

            best_idx = int(np.argmax(scores))
            best_key = excel_keys[best_idx]

            results.append({
                "box": field["box"],
                "value": excel_data.get(best_key, ""),
                "confidence": float(scores[best_idx])
            })

        return results

    # -------------------------------
    # PDF WRITING
    # -------------------------------
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

    # -------------------------------
    # HELPERS
    # -------------------------------
    def _normalize_box(self, box, shape):
        h, w = shape[:2]
        return [
            int(1000 * box[0][0] / w),
            int(1000 * box[0][1] / h),
            int(1000 * box[2][0] / w),
            int(1000 * box[2][1] / h)
        ]
