"""
Gemini Vision OCR extraction service for PS-2 AI Document Forensics.
Extracts verbatim text lines, words, and bounding boxes directly from images
when Tesseract CLI is unavailable (e.g. serverless environments like AWS Lambda / Netlify).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_gemini_vision_ocr(
    image_path: Path,
    api_key: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Extracts text lines and normalized 150 DPI bounding boxes from a document image
    using Google Gemini Vision (gemini-1.5-flash).
    """
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key or not image_path.exists():
        return None

    try:
        import google.generativeai as genai
        from PIL import Image

        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json", "temperature": 0.0},
        )

        with Image.open(image_path) as pil_img:
            w, h = pil_img.size
            prompt = """You are an OCR and document extraction engine.
Extract all visible text from this document image line-by-line verbatim.
Preserve exact spelling, numbers, dates, currency symbols, and punctuation.
For each visual text line or key-value pair, provide:
- "text": The exact text content
- "bbox": [x0, y0, x1, y1] pixel bounding box coordinates scaled to image width and height.

Return a valid JSON array of objects:
[
  {"text": "State Bank of India", "bbox": [150, 40, 500, 70]},
  {"text": "TRANSACTION SLIP", "bbox": [250, 90, 550, 120]}
]"""
            response = model.generate_content([prompt, pil_img])
            content = response.text.strip()
            data = json.loads(content)

            if not isinstance(data, list):
                return None

            words = []
            for idx, item in enumerate(data):
                txt = str(item.get("text", "")).strip()
                if not txt:
                    continue
                raw_box = item.get("bbox", [0, 0, w, 20])
                if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
                    bbox = [int(raw_box[0]), int(raw_box[1]), int(raw_box[2]), int(raw_box[3])]
                else:
                    bbox = [0, idx * 25, w, idx * 25 + 20]

                words.append({
                    "text": txt,
                    "bbox": bbox,
                    "confidence": 0.98,
                    "source": "ocr",
                    "block_no": 1,
                    "line_no": idx + 1,
                    "word_no": 1,
                })

            return words
    except Exception:
        return None
