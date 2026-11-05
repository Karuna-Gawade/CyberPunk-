"""
PDF Text-Layer extraction service using PyMuPDF.
Extracts vector text, word coordinates, and font/span metadata.
Converts PDF 72-DPI points directly to fixed 150-DPI render pixel coordinates.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple
import fitz  # PyMuPDF


def points_to_150_dpi(bbox: Tuple[float, float, float, float]) -> List[int]:
    """Converts PyMuPDF 72 DPI points to fixed 150 DPI coordinates [x0, y0, x1, y1]."""
    scale = 150.0 / 72.0
    return [
        int(round(bbox[0] * scale)),
        int(round(bbox[1] * scale)),
        int(round(bbox[2] * scale)),
        int(round(bbox[3] * scale)),
    ]


def extract_pdf_text_layer(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts text, word boxes, and detailed span metadata for every page.
    Returns:
      [
        {
          "page": 1,
          "full_text": "...",
          "words": [
             {"text": "...", "bbox": [x0, y0, x1, y1], "confidence": 1.0, "source": "text_layer"}
          ],
          "spans": [
             {"text": "...", "bbox": [x0, y0, x1, y1], "font": "Helvetica", "size": 12.0, "color": 0}
          ]
        }, ...
      ]
    """
    pages_data = []
    doc = fitz.open(file_path)

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        full_text = page.get_text("text")

        # Extract words: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        raw_words = page.get_text("words")
        words = []
        for w in raw_words:
            pt_box = (w[0], w[1], w[2], w[3])
            words.append({
                "text": w[4],
                "bbox": points_to_150_dpi(pt_box),
                "confidence": 0.99,  # High confidence for direct digital vector text
                "source": "text_layer",
                "block_no": w[5],
                "line_no": w[6],
                "word_no": w[7],
            })

        # Extract dict spans for forensic inspection (fonts, sizes, colors)
        page_dict = page.get_text("dict")
        spans = []
        for block in page_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        pt_box = (span["bbox"][0], span["bbox"][1], span["bbox"][2], span["bbox"][3])
                        spans.append({
                            "text": span["text"],
                            "bbox": points_to_150_dpi(pt_box),
                            "font": span["font"],
                            "size": span["size"],
                            "color": span["color"],
                            "flags": span.get("flags", 0),
                        })

        pages_data.append({
            "page": page_idx + 1,
            "full_text": full_text,
            "words": words,
            "spans": spans,
        })

    doc.close()
    return pages_data
