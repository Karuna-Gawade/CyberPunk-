"""
Unit tests for document classification heuristics.
"""

from backend.app.models.contracts import DocumentType
from backend.app.services.classification import classify_document_text


def test_classify_aadhaar_text():
    text = "Government of India Unique Identification Authority of India 5489 1234 5674 Mera Aadhaar"
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.AADHAAR
    assert conf >= 0.70


def test_classify_pan_text():
    text = "Income Tax Department Govt. of India Permanent Account Number BCDPS1234E Father's Name"
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.PAN
    assert conf >= 0.70


def test_classify_salary_slip_text():
    text = "Apex Technologies Payslip for the month of October 2026 Basic Salary Gross Earnings Net Pay EPF"
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.SALARY_SLIP
    assert conf >= 0.70


def test_classify_bank_statement_text():
    text = "Axis Bank Statement of Account Account Holder Opening Balance Closing Balance IFSC UTIB0000123"
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.BANK_STATEMENT
    assert conf >= 0.70


def test_classify_unsupported_text():
    text = "Random Grocery Store Invoice Invoice #1234 Apples Oranges Milk Total: $15.00 Thank you!"
    doc_type, conf = classify_document_text(text)
    assert doc_type == DocumentType.UNSUPPORTED
    assert conf == 0.0
