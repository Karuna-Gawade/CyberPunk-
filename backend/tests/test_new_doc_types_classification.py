"""
Unit tests for the classification of new document types:
Loan Application, Form 15G, and Payment Instruction.
"""

from backend.app.models.contracts import DocumentType
from backend.app.services.classification import classify_document_text


def test_classify_loan_application_text():
    text = (
        "Personal Loan Application Form\n"
        "Applicant Name: Rajesh Sharma\n"
        "Date of Birth: 14/05/1988\n"
        "PAN Number: BCDPS1234E\n"
        "Declared Monthly Income: Rs. 85000\n"
        "Requested Loan Amount: Rs. 500000\n"
        "Loan Purpose: Home Renovation\n"
        "Applicant Signature"
    )
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.LOAN_APPLICATION
    assert conf >= 0.70


def test_classify_declaration_15g_text():
    text = (
        "Form No. 15G Declaration under section 197A(1)\n"
        "Name of Assessee: Rajesh Sharma\n"
        "PAN of Assessee: BCDPS1234E\n"
        "Financial Year: 2026-2027\n"
        "Estimated Total Income: Rs. 240000\n"
        "Date of Declaration: 01/04/2026\n"
        "Signature of Declarant"
    )
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.DECLARATION_15G
    assert conf >= 0.70


def test_classify_payment_instruction_text():
    text = (
        "Payment Transfer Instruction Mandate NEFT / RTGS\n"
        "Remitter Name: Rajesh Sharma\n"
        "Debit Account Number: 912010045678912\n"
        "Beneficiary Name: Priya Sharma\n"
        "Transfer Amount: Rs. 50000\n"
        "Instruction Date: 12/10/2026\n"
        "Authorized Signature"
    )
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.PAYMENT_INSTRUCTION
    assert conf >= 0.70


def test_classify_unrelated_text_fallback():
    text = "The quick brown fox jumps over the lazy dog in a poetic landscape with no banking or tax terms."
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.UNSUPPORTED
    assert conf == 0.0
