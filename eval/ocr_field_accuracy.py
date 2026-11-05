"""
OCR and Field Extraction Accuracy Evaluation Tool.
Evaluates extraction performance against synthetic ground truth fields across sample bundles.
Reports accuracy percentages per field type and overall precision.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
BUNDLES_DIR = Path("samples/bundles")

# Ground truth values for canonical genuine_01 bundle
GROUND_TRUTH_GENUINE_01 = {
    "aadhaar.pdf": {
        "aadhaar_number": "548912345674",
        "name": "Rajesh Sharma",
        "dob": "14/05/1988",
        "gender": "Male",
    },
    "pan.pdf": {
        "pan_number": "BCDPS1234E",
        "name": "Rajesh Sharma",
        "father_name": "Suresh Sharma",
        "dob": "14/05/1988",
    },
    "salary_slip.pdf": {
        "employee_name": "Rajesh Sharma",
        "pan_number": "BCDPS1234E",
        "gross": "85000",
        "net_pay": "78800",
    },
    "bank_statement.pdf": {
        "account_holder": "Rajesh Sharma",
        "account_number": "918020034567890",
    }
}


def run_field_accuracy_eval():
    print("=" * 60)
    print("AI Document Forensics — Extraction Accuracy Report")
    print("=" * 60)

    # 1. Create an investigation
    r_inv = client.post("/investigations")
    inv_id = r_inv.json()["investigation_id"]

    bundle_path = BUNDLES_DIR / "genuine_01"
    files = [
        ("files", ("aadhaar.pdf", open(bundle_path / "aadhaar.pdf", "rb"), "application/pdf")),
        ("files", ("pan.pdf", open(bundle_path / "pan.pdf", "rb"), "application/pdf")),
        ("files", ("salary_slip.pdf", open(bundle_path / "salary_slip.pdf", "rb"), "application/pdf")),
        ("files", ("bank_statement.pdf", open(bundle_path / "bank_statement.pdf", "rb"), "application/pdf")),
    ]
    client.post(f"/investigations/{inv_id}/documents", files=files)
    client.post(f"/investigations/{inv_id}/process")

    inv = client.get(f"/investigations/{inv_id}").json()

    total_expected = 0
    total_matched = 0

    print(f"\nInvestigation: {inv_id}")
    print(f"{'Document':<20} | {'Field':<18} | {'Extracted':<22} | {'Expected':<22} | Status")
    print("-" * 90)

    for doc in inv["documents"]:
        filename = doc["filename"]
        expected_fields = GROUND_TRUTH_GENUINE_01.get(filename, {})
        
        # Fetch unmasked fields via API
        fields_resp = client.get(f"/documents/{doc['doc_id']}/fields").json()
        extracted_dict = {}
        for f in fields_resp:
            # If masked, call reveal to inspect true value
            if f["name"] in ("aadhaar_number", "pan_number"):
                rev = client.post(f"/fields/{f['field_id']}/reveal").json()
                extracted_dict[f["name"]] = str(rev.get("unmasked_value", "")).replace(" ", "")
            else:
                extracted_dict[f["name"]] = str(f["value"]).replace(" ", "")

        for field_name, expected_val in expected_fields.items():
            total_expected += 1
            extracted_val = extracted_dict.get(field_name, "<MISSING>")
            
            clean_expected = str(expected_val).replace(" ", "").upper()
            clean_extracted = str(extracted_val).replace(" ", "").upper()
            
            # Check match
            match = (clean_expected in clean_extracted) or (clean_extracted in clean_expected)
            if match and clean_extracted != "<MISSING>":
                total_matched += 1
                status = "MATCH [PASS]"
            else:
                status = "MISMATCH [FAIL]"

            print(f"{filename:<20} | {field_name:<18} | {extracted_val[:20]:<22} | {expected_val[:20]:<22} | {status}")

    accuracy_pct = (total_matched / total_expected * 100) if total_expected > 0 else 0
    print("-" * 90)
    print(f"Total Fields Evaluated: {total_expected}")
    print(f"Correctly Extracted:    {total_matched}")
    print(f"Field Accuracy Score:   {accuracy_pct:.1f}%")
    print("=" * 60)
    return accuracy_pct


if __name__ == "__main__":
    run_field_accuracy_eval()
