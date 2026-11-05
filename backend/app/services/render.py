"""
Document rendering service.
Renders PDF and image documents server-side to PNG images at a fixed 150 DPI.
"""

from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
import cv2


def render_document_pages(file_path: Path, output_dir: Path, target_dpi: int = 150) -> List[Path]:
    """
    Renders every page of a PDF or image file into PNG format at fixed 150 DPI.
    Returns list of paths to rendered PNG images: [page_1.png, page_2.png, ...]
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths: List[Path] = []
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        doc = fitz.open(file_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=target_dpi)
            out_file = output_dir / f"page_{page_idx + 1}.png"
            pix.save(str(out_file))
            rendered_paths.append(out_file)
        doc.close()
    elif suffix in (".png", ".jpg", ".jpeg"):
        img = cv2.imread(str(file_path))
        if img is not None:
            out_file = output_dir / "page_1.png"
            cv2.imwrite(str(out_file), img)
            rendered_paths.append(out_file)
        else:
            raise ValueError(f"Unable to read image file: {file_path}")
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")

    return rendered_paths


def get_rendered_page_path(rendered_dir: Path, doc_id: str, page_number: int) -> Path:
    """Returns the expected path to the rendered 150 DPI PNG for a given doc and page."""
    return rendered_dir / doc_id / f"page_{page_number}.png"
