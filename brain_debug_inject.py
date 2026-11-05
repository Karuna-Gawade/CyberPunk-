import sys
sys.path.insert(0, ".")
import pymupdf as fitz
from backend.app.services.injection import scan_spans_for_injections, scan_text_for_injections

pdf_path = "samples/bundles/tampered_10_prompt_injection/salary_slip.pdf"
pdoc = fitz.open(pdf_path)
for pnum, page in enumerate(pdoc, start=1):
    pdict = page.get_text("dict")
    spans = []
    for b in pdict.get("blocks", []):
        for l in b.get("lines", []):
            spans.extend(l.get("spans", []))
    print(f"Page {pnum}: {len(spans)} spans")
    for s in spans:
        print(f"  color={s.get('color')} size={s.get('size')} text={repr(s['text'][:80])}")
    
    inject = scan_spans_for_injections(spans, "TEST_DOC", page_num=pnum)
    print(f"  -> Injection findings from spans: {len(inject)}")
    for f in inject:
        print(f"     {f.title}")
    
    full_text = page.get_text("text")
    text_inject = scan_text_for_injections(full_text, "TEST_DOC", page_num=pnum)
    print(f"  -> Injection findings from full text: {len(text_inject)}")
    for f in text_inject:
        print(f"     {f.title}")
pdoc.close()
